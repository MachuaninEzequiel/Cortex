"""cortex.documentation.migration - Vault backfill to the canonical schema.

Reads every ``.md`` file in a vault, infers the DocType from the path,
builds a canonical frontmatter, and either reports the diff (dry-run) or
rewrites the file (``apply=True``).

Idempotency: a file whose frontmatter already declares ``schema_version: 1``
and a known ``doc_type`` is skipped. Re-running on a migrated vault is a
no-op (unless ``force=True``).

Backwards-compat: legacy fields not part of the canonical schema are
preserved under a ``legacy_<name>`` prefix so they remain auditable.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

import yaml

from cortex.documentation.backup import create_backup
from cortex.documentation.common import (
    compute_fingerprint,
    parse_frontmatter_lenient,
    slugify,
    split_frontmatter_and_body,
    yaml_dump_safe,
)
from cortex.documentation.doc_type import VALID_STATUSES, DocType, doc_type_from_path

logger = logging.getLogger(__name__)

# Fields the canonical schema produces by itself. Legacy keys outside this
# set are preserved under ``legacy_<name>``.
_CANONICAL_TOP_LEVEL = frozenset({
    "schema_version", "doc_type", "title", "created_at", "updated_at",
    "tags", "status", "links", "vault_scope", "fingerprint",
    "owner", "team", "classification", "retention_days", "audit_trail",
})

# Fields we know how to map from legacy notes onto the canonical schema.
_LEGACY_MAPPED = frozenset({"date", "title", "tags", "status"})

# Type-specific extras we explicitly preserve (do not legacy-prefix them).
_TYPE_SPECIFIC_FIELDS = frozenset({
    # ADR / Decision
    "adr_number", "supersedes", "superseded_by", "alternatives_considered",
    "acceptance_criteria_met", "reversible_within_days",
    # Incident / Postmortem
    "incident_number", "severity", "opened_at", "closed_at",
    "affected_services", "root_cause_postmortem", "incident_path",
    # Runbook
    "runbook_kind", "applies_to", "estimated_duration_minutes",
    "last_verified_at",
    # Architecture
    "related_adrs",
    # Changelog
    "version", "release_date",
    # HU
    "external_id", "source", "kind", "assignee", "external_url", "synced_at",
    # Session / Handoff
    "session_id", "pr", "branch", "commit", "cortex_telemetry",
    "parent_session_id",
    # Glossary
    "term", "domain", "related_terms",
})

_ADR_NUMBER_RE = re.compile(r"^ADR-(\d+)", re.IGNORECASE)
_INC_NUMBER_RE = re.compile(r"^INC-(\d+)", re.IGNORECASE)
_PM_NUMBER_RE = re.compile(r"^PM-(\d+)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class NoteDiff:
    """Description of a single migration step."""

    path: Path
    action: str  # "migrate" | "skip" | "unclassifiable"
    doc_type: DocType | None = None
    legacy_fm: dict[str, Any] = field(default_factory=dict)
    new_fm: dict[str, Any] = field(default_factory=dict)
    reason: str = ""


@dataclass
class MigrationResult:
    """Aggregated outcome of a ``migrate_vault`` call."""

    total_scanned: int = 0
    migrated: list[NoteDiff] = field(default_factory=list)
    already_migrated: list[NoteDiff] = field(default_factory=list)
    unclassifiable: list[NoteDiff] = field(default_factory=list)
    errors: list[NoteDiff] = field(default_factory=list)
    backup_path: Path | None = None
    applied: bool = False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def migrate_vault(
    vault_path: Path,
    *,
    apply: bool = False,
    force: bool = False,
    path_filter: Path | None = None,
    preserve_legacy: bool = True,
    create_backup_archive: bool = True,
    now: datetime | None = None,
) -> MigrationResult:
    """Migrate ``vault_path`` to the canonical schema.

    Args:
        vault_path: vault root (the directory containing subfolders).
        apply: if False (default), no files are written.
        force: re-migrate notes that already declare schema_version=1.
        path_filter: optional subpath to scan (must live inside vault_path).
        preserve_legacy: keep unmapped legacy keys under ``legacy_<name>``.
        create_backup_archive: create a .tar.gz snapshot before writing.
        now: clock injection (tests).

    Returns:
        ``MigrationResult`` with the per-note diffs and aggregate stats.
    """
    now = now or datetime.now(UTC)
    result = MigrationResult(applied=apply)

    if not vault_path.exists():
        return result

    scan_root = path_filter if path_filter else vault_path
    md_files = sorted(scan_root.rglob("*.md"))

    diffs: list[NoteDiff] = []
    for md in md_files:
        if vault_path / ".cortex" / "backups" in md.parents:
            continue
        if "_archived" in md.parts:
            continue
        result.total_scanned += 1
        try:
            diff = _compute_diff(
                md, vault_path,
                force=force, preserve_legacy=preserve_legacy, now=now,
            )
        except Exception as exc:  # pragma: no cover - defensive
            diff = NoteDiff(path=md, action="error", reason=str(exc))
            result.errors.append(diff)
            continue
        diffs.append(diff)

    if apply and create_backup_archive:
        result.backup_path = create_backup(vault_path)

    for diff in diffs:
        if diff.action == "migrate":
            if apply:
                _apply_diff(diff)
            result.migrated.append(diff)
        elif diff.action == "skip":
            result.already_migrated.append(diff)
        elif diff.action == "unclassifiable":
            result.unclassifiable.append(diff)

    return result


def validate_vault(vault_path: Path) -> dict[str, Any]:
    """Validate every note in ``vault_path`` against the canonical schema.

    Returns a payload with per-note results plus aggregate counters.
    """
    from cortex.documentation.errors import SchemaValidationError, UnknownDocTypeError
    from cortex.documentation.validation import validate_path_frontmatter

    out: dict[str, Any] = {
        "vault_path": str(vault_path),
        "total": 0,
        "valid": 0,
        "invalid": 0,
        "no_frontmatter": 0,
        "issues": [],
    }
    if not vault_path.exists():
        return out
    for md in sorted(vault_path.rglob("*.md")):
        if "_archived" in md.parts:
            continue
        out["total"] += 1
        try:
            validate_path_frontmatter(md)
            out["valid"] += 1
        except (SchemaValidationError, UnknownDocTypeError) as exc:
            out["invalid"] += 1
            out["issues"].append({
                "path": str(md.relative_to(vault_path)),
                "error": str(exc),
            })
    out["no_frontmatter"] = max(out["total"] - out["valid"] - out["invalid"], 0)
    return out


def format_report(result: MigrationResult) -> str:
    """Human-readable summary of a ``MigrationResult``."""
    lines: list[str] = []
    mode = "APPLY" if result.applied else "DRY-RUN"
    lines.append(f"# Migration Report ({mode})")
    lines.append("")
    lines.append(f"- Total scanned: {result.total_scanned}")
    lines.append(f"- Migrated: {len(result.migrated)}")
    lines.append(f"- Already migrated (skipped): {len(result.already_migrated)}")
    lines.append(f"- Unclassifiable: {len(result.unclassifiable)}")
    lines.append(f"- Errors: {len(result.errors)}")
    if result.backup_path:
        lines.append(f"- Backup: {result.backup_path}")
    if result.unclassifiable:
        lines.append("")
        lines.append("## Unclassifiable notes")
        for diff in result.unclassifiable:
            lines.append(f"- {diff.path} ({diff.reason})")
    if result.errors:
        lines.append("")
        lines.append("## Errors")
        for diff in result.errors:
            lines.append(f"- {diff.path}: {diff.reason}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal: diff computation
# ---------------------------------------------------------------------------


def _compute_diff(
    md_path: Path,
    vault_root: Path,
    *,
    force: bool,
    preserve_legacy: bool,
    now: datetime,
) -> NoteDiff:
    legacy_fm = parse_frontmatter_lenient(md_path)

    if not force and legacy_fm.get("schema_version") == 1 and isinstance(
        legacy_fm.get("doc_type"), str,
    ):
        return NoteDiff(
            path=md_path, action="skip", legacy_fm=legacy_fm,
            reason="schema_version=1 already present",
        )

    try:
        relative = md_path.relative_to(vault_root)
    except ValueError:
        return NoteDiff(
            path=md_path, action="unclassifiable",
            reason="path outside vault root",
        )

    inferred = doc_type_from_path(relative)
    if inferred is None:
        return NoteDiff(
            path=md_path, action="unclassifiable", legacy_fm=legacy_fm,
            reason=f"unable to infer doc_type from path {relative.as_posix()!r}",
        )

    new_fm = _build_new_frontmatter(
        md_path, legacy_fm, inferred, vault_root, preserve_legacy, now,
    )
    return NoteDiff(
        path=md_path, action="migrate", doc_type=inferred,
        legacy_fm=legacy_fm, new_fm=new_fm,
    )


def _build_new_frontmatter(
    md_path: Path,
    legacy: dict[str, Any],
    doc_type: DocType,
    vault_root: Path,
    preserve_legacy: bool,
    now: datetime,
) -> dict[str, Any]:
    created_at = _resolve_datetime(legacy.get("created_at") or legacy.get("date"), md_path, now)
    updated_at = _resolve_datetime(legacy.get("updated_at"), md_path, now)
    if updated_at < created_at:
        updated_at = created_at

    body = _read_body(md_path)
    fingerprint = compute_fingerprint(body)

    new: dict[str, Any] = {
        "schema_version": 1,
        "doc_type": doc_type.value,
        "title": legacy.get("title") or md_path.stem.replace("_", " ").title(),
        "created_at": created_at.isoformat(),
        "updated_at": updated_at.isoformat(),
        "tags": _resolve_tags(legacy.get("tags")),
        "status": _resolve_status(legacy.get("status"), doc_type),
        "links": _extract_wiki_links(body),
        "vault_scope": "local",
        "fingerprint": fingerprint,
    }
    new.update(_type_specific_for(doc_type, md_path, legacy))

    if preserve_legacy:
        for key, value in legacy.items():
            if key in _CANONICAL_TOP_LEVEL or key in _LEGACY_MAPPED:
                continue
            if key in _TYPE_SPECIFIC_FIELDS:
                continue
            new[f"legacy_{key}"] = value

    return new


def _apply_diff(diff: NoteDiff) -> None:
    body = _read_body(diff.path)
    new_yaml = yaml_dump_safe(diff.new_fm)
    diff.path.write_text(
        "---\n" + new_yaml + "---\n\n" + body, encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Internal: field resolvers
# ---------------------------------------------------------------------------


def _read_body(md_path: Path) -> str:
    raw = md_path.read_text(encoding="utf-8")
    _, body = split_frontmatter_and_body(raw)
    return body.lstrip("\n")


def _resolve_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(t) for t in value]
    return []


def _resolve_status(value: Any, doc_type: DocType) -> str:
    valid = VALID_STATUSES[doc_type]
    if isinstance(value, str) and value in valid:
        return value
    # Legacy "generated"/"in_progress" mappings.
    if isinstance(value, str):
        normalized = value.lower().replace(" ", "_").replace("-", "_")
        canonical_map: dict[str, dict[str, str]] = {
            "session": {"generated": "completed", "fallback": "fallback"},
            "hu": {"imported": "backlog", "in_progress": "in-progress"},
        }
        mapped = canonical_map.get(doc_type.value, {}).get(normalized)
        if mapped and mapped in valid:
            return mapped
    return next(iter(sorted(valid)))


def _resolve_datetime(value: Any, path: Path, now: datetime) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except ValueError:
            pass
    # Fallback: file mtime.
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, UTC)
    except OSError:
        return now


_WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")


def _extract_wiki_links(body: str) -> list[str]:
    if not body:
        return []
    return sorted(set(_WIKI_LINK_RE.findall(body)))


def _type_specific_for(
    doc_type: DocType, md_path: Path, legacy: dict[str, Any],
) -> dict[str, Any]:
    """Compute the minimum type-specific fields required by each schema."""
    stem = md_path.stem
    if doc_type is DocType.ADR:
        m = _ADR_NUMBER_RE.match(stem)
        return {
            "adr_number": int(m.group(1)) if m else int(legacy.get("adr_number") or 1),
            "supersedes": list(legacy.get("supersedes") or []),
            "superseded_by": legacy.get("superseded_by"),
            "alternatives_considered": list(legacy.get("alternatives_considered") or []),
            "acceptance_criteria_met": bool(legacy.get("acceptance_criteria_met") or False),
        }
    if doc_type is DocType.INCIDENT:
        m = _INC_NUMBER_RE.match(stem)
        return {
            "incident_number": int(m.group(1)) if m else int(legacy.get("incident_number") or 1),
            "severity": legacy.get("severity") or "medium",
            "opened_at": _resolve_datetime(legacy.get("opened_at") or legacy.get("date"), md_path, datetime.now(UTC)).isoformat(),
            "closed_at": legacy.get("closed_at"),
            "affected_services": list(legacy.get("affected_services") or []),
            "root_cause_postmortem": legacy.get("root_cause_postmortem"),
        }
    if doc_type is DocType.POSTMORTEM:
        m = _PM_NUMBER_RE.match(stem)
        return {
            "incident_number": int(m.group(1)) if m else int(legacy.get("incident_number") or 1),
            "incident_path": legacy.get("incident_path") or "",
            "severity": legacy.get("severity") or "medium",
        }
    if doc_type is DocType.RUNBOOK:
        return {
            "runbook_kind": legacy.get("runbook_kind") or "operational",
            "applies_to": list(legacy.get("applies_to") or []),
            "estimated_duration_minutes": int(legacy.get("estimated_duration_minutes") or 0),
            "last_verified_at": legacy.get("last_verified_at"),
        }
    if doc_type is DocType.SESSION:
        return {
            "session_id": legacy.get("session_id") or _derive_session_id(md_path),
            "pr": legacy.get("pr"),
            "branch": legacy.get("branch"),
            "commit": legacy.get("commit"),
            "cortex_telemetry": legacy.get("cortex_telemetry"),
        }
    if doc_type is DocType.HANDOFF:
        return {
            "parent_session_id": legacy.get("parent_session_id") or "unknown",
        }
    if doc_type is DocType.HU:
        return {
            "external_id": legacy.get("external_id") or stem,
            "source": legacy.get("source") or "unknown",
            "kind": legacy.get("kind") or "story",
            "assignee": legacy.get("assignee"),
            "external_url": legacy.get("external_url"),
            "synced_at": legacy.get("synced_at"),
        }
    if doc_type is DocType.GLOSSARY:
        term = legacy.get("term") or stem.replace("-", " ").title()
        return {"term": term, "domain": legacy.get("domain"),
                "related_terms": list(legacy.get("related_terms") or [])}
    if doc_type is DocType.CHANGELOG:
        return {
            "version": legacy.get("version") or stem,
            "release_date": legacy.get("release_date"),
        }
    if doc_type is DocType.DECISION:
        return {
            "reversible_within_days": int(legacy.get("reversible_within_days") or 0),
        }
    if doc_type is DocType.ARCHITECTURE:
        return {
            "related_adrs": list(legacy.get("related_adrs") or []),
        }
    if doc_type is DocType.SPEC:
        return {}
    return {}


_SESSION_ID_PREFIX_RE = re.compile(r"\d{4}-\d{2}-\d{2}_([a-f0-9]{6,})", re.IGNORECASE)


def _derive_session_id(path: Path) -> str:
    m = _SESSION_ID_PREFIX_RE.search(path.stem)
    if m:
        return m.group(1)[:12]
    return slugify(path.stem)[:12] or "unknown00000"


__all__ = [
    "MigrationResult",
    "NoteDiff",
    "format_report",
    "migrate_vault",
    "validate_vault",
]
