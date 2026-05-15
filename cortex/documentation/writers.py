"""cortex.documentation.writers - Canonical writers for the 9 new DocTypes.

Each ``write_X_note`` function follows the exact same shape:

    def write_X_note(
        data: XData,
        *,
        vault,                               # has .path: Path and .index_file(rel)
        vault_scope: str = "local",
        project_id: str | None = None,
        actor: str | None = None,
        overwrite: bool = False,
    ) -> Path:

This module covers the 9 new types from Fase 03 plus the 3 canonical writers
for the legacy SESSION / SPEC / HU types added in Fase 04
(``write_session_note_canonical``, ``write_spec_note_canonical``,
``write_hu_note``).
"""

from __future__ import annotations

import re
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from pydantic import ValidationError

from cortex.documentation.audit import append_audit_event
from cortex.documentation.common import (
    compute_fingerprint,
    slugify,
    yaml_dump_safe,
)
from cortex.documentation.data import (
    ADRData,
    ArchitectureData,
    ChangelogData,
    DecisionData,
    GlossaryEntryData,
    HandoffData,
    HUData,
    IncidentData,
    PostmortemData,
    RunbookData,
    SessionData,
    SpecData,
)
from cortex.documentation.doc_type import VALID_STATUSES, DocType
from cortex.documentation.errors import (
    DuplicateDocumentError,
    SchemaValidationError,
)
from cortex.documentation.routing import (
    RouteSpec,
    render_filename,
    resolve_route,
    resolve_target_path,
)
from cortex.documentation.schemas import (
    SCHEMA_BY_TYPE,
    SCHEMA_BY_TYPE_ENTERPRISE,
    CommonFrontmatter,
)
from cortex.documentation.schemas.base import EnterpriseFrontmatter
from cortex.documentation.templates_engine import render_template


# ---------------------------------------------------------------------------
# Vault protocol (duck-typed).
# ---------------------------------------------------------------------------


class VaultLike(Protocol):
    """Subset of VaultReader used by canonical writers."""

    @property
    def path(self) -> Path:  # noqa: D401 - protocol
        ...

    def index_file(self, relative_path: str) -> bool:  # noqa: D401 - protocol
        ...


# ---------------------------------------------------------------------------
# Helpers shared by all writers.
# ---------------------------------------------------------------------------


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _default_status(doc_type: DocType) -> str:
    """First valid status for ``doc_type`` (used when data.status is empty)."""
    return next(iter(sorted(VALID_STATUSES[doc_type])))


def _coerce_status(doc_type: DocType, requested: str) -> str:
    """Return ``requested`` if valid for ``doc_type`` else first valid status."""
    if requested and requested in VALID_STATUSES[doc_type]:
        return requested
    return _default_status(doc_type)


_ADR_NUM_RE = re.compile(r"^ADR-(\d+)", re.IGNORECASE)
_INC_NUM_RE = re.compile(r"^INC-(\d+)", re.IGNORECASE)


def _next_number(folder: Path, regex: re.Pattern[str]) -> int:
    """Find the next available numeric prefix in ``folder``.

    Returns 1 if folder is empty or doesn't exist.
    """
    if not folder.exists():
        return 1
    used = []
    for entry in folder.iterdir():
        if not entry.is_file():
            continue
        match = regex.match(entry.stem)
        if match:
            try:
                used.append(int(match.group(1)))
            except ValueError:
                continue
    return (max(used) + 1) if used else 1


def _next_adr_number(vault: VaultLike) -> int:
    return _next_number(vault.path / "decisions", _ADR_NUM_RE)


def _next_incident_number(vault: VaultLike) -> int:
    return _next_number(vault.path / "incidents", _INC_NUM_RE)


def _require_enterprise_fields(data: Any, vault_scope: str) -> None:
    if vault_scope != "enterprise":
        return
    missing = []
    if not getattr(data, "owner", None):
        missing.append("owner")
    if not getattr(data, "team", None):
        missing.append("team")
    if missing:
        raise SchemaValidationError(
            f"Enterprise scope requires fields: {missing}"
        )


def _build_filename_context(
    data: Any,
    doc_type: DocType,
    vault: VaultLike,
) -> dict[str, Any]:
    """Build the context dict required by ``render_filename`` for this doc_type."""
    today = _now_utc().strftime("%Y-%m-%d")
    title_slug = slugify(getattr(data, "title", "")) or "untitled"
    ctx: dict[str, Any] = {"date": today, "slug": title_slug}

    if doc_type == DocType.ADR:
        number = data.adr_number if data.adr_number > 0 else _next_adr_number(vault)
        ctx["number"] = number
        # Also expose back to the caller so the writer can update data.adr_number
        # for the frontmatter.
        ctx["_adr_number"] = number
    elif doc_type == DocType.DECISION:
        # date + slug only (already set)
        pass
    elif doc_type == DocType.INCIDENT:
        number = data.incident_number if data.incident_number > 0 else _next_incident_number(vault)
        ctx["number"] = number
        ctx["_incident_number"] = number
    elif doc_type == DocType.POSTMORTEM:
        ctx["incident_number"] = data.incident_number
    elif doc_type == DocType.HANDOFF:
        pass
    elif doc_type == DocType.SESSION:
        ctx["session_id"] = data.session_id
    elif doc_type == DocType.SPEC:
        # date + slug only (already set)
        pass
    elif doc_type == DocType.HU:
        ctx = {"external_id": data.external_id}
    elif doc_type == DocType.RUNBOOK:
        ctx = {"slug": title_slug}
    elif doc_type == DocType.ARCHITECTURE:
        ctx = {"slug": title_slug}
    elif doc_type == DocType.CHANGELOG:
        ctx = {"version": data.version}
    elif doc_type == DocType.GLOSSARY:
        ctx = {"term_slug": slugify(data.term)}
    return ctx


def _common_frontmatter_fields(
    data: Any,
    doc_type: DocType,
    fingerprint: str,
    vault_scope: str,
) -> dict[str, Any]:
    now = _now_utc()
    return {
        "schema_version": 1,
        "doc_type": doc_type.value,
        "title": data.title,
        "created_at": now,
        "updated_at": now,
        "tags": list(data.tags or []),
        "status": _coerce_status(doc_type, data.status),
        "links": list(data.links or []),
        "vault_scope": vault_scope,
        "fingerprint": fingerprint,
    }


def _enterprise_fields(data: Any) -> dict[str, Any]:
    return {
        "owner": data.owner,
        "team": data.team,
        "classification": data.classification or "internal",
        "retention_days": data.retention_days or 0,
        "audit_trail": [],
    }


def _type_specific_fields(
    data: Any, doc_type: DocType, filename_ctx: dict[str, Any]
) -> dict[str, Any]:
    """Extract DocType-specific fields from ``data`` into a frontmatter dict."""
    if doc_type == DocType.ADR:
        return {
            "adr_number": filename_ctx.get("_adr_number", data.adr_number),
            "supersedes": list(data.supersedes or []),
            "superseded_by": data.superseded_by,
            "alternatives_considered": list(data.alternatives_considered or []),
            "acceptance_criteria_met": data.acceptance_criteria_met,
        }
    if doc_type == DocType.DECISION:
        return {"reversible_within_days": data.reversible_within_days}
    if doc_type == DocType.INCIDENT:
        return {
            "incident_number": filename_ctx.get("_incident_number", data.incident_number),
            "severity": data.severity,
            "opened_at": data.opened_at or _now_utc(),
            "closed_at": data.closed_at,
            "affected_services": list(data.affected_services or []),
            "root_cause_postmortem": data.root_cause_postmortem,
        }
    if doc_type == DocType.POSTMORTEM:
        return {
            "incident_number": data.incident_number,
            "incident_path": data.incident_path,
            "severity": data.severity,
        }
    if doc_type == DocType.RUNBOOK:
        return {
            "runbook_kind": data.runbook_kind,
            "applies_to": list(data.applies_to or []),
            "estimated_duration_minutes": data.estimated_duration_minutes,
            "last_verified_at": data.last_verified_at,
        }
    if doc_type == DocType.ARCHITECTURE:
        return {"related_adrs": list(data.related_adrs or [])}
    if doc_type == DocType.CHANGELOG:
        return {
            "version": data.version,
            "release_date": data.release_date,
        }
    if doc_type == DocType.HU:
        return {
            "external_id": data.external_id,
            "source": data.source,
            "kind": data.kind,
            "assignee": data.assignee,
            "external_url": data.external_url,
            "synced_at": data.synced_at,
        }
    if doc_type == DocType.GLOSSARY:
        return {
            "term": data.term,
            "domain": data.domain,
            "related_terms": list(data.related_terms or []),
        }
    if doc_type == DocType.HANDOFF:
        return {"parent_session_id": data.parent_session_id}
    if doc_type == DocType.SESSION:
        return {
            "session_id": data.session_id,
            "pr": data.pr,
            "branch": data.branch,
            "commit": data.commit,
            "cortex_telemetry": data.cortex_telemetry,
        }
    if doc_type == DocType.SPEC:
        # No type-specific fields beyond the common frontmatter.
        return {}
    return {}


def _build_frontmatter(
    data: Any,
    doc_type: DocType,
    fingerprint: str,
    vault_scope: str,
    actor: str | None,
    filename_ctx: dict[str, Any],
) -> CommonFrontmatter:
    raw = _common_frontmatter_fields(data, doc_type, fingerprint, vault_scope)
    raw.update(_type_specific_fields(data, doc_type, filename_ctx))
    schema_cls: type[CommonFrontmatter]
    if vault_scope == "enterprise":
        raw.update(_enterprise_fields(data))
        schema_cls = SCHEMA_BY_TYPE_ENTERPRISE[doc_type]
    else:
        schema_cls = SCHEMA_BY_TYPE[doc_type]
    try:
        fm = schema_cls.model_validate(raw)
    except ValidationError as exc:
        raise SchemaValidationError(
            f"Frontmatter validation failed for {doc_type.value}: {exc}"
        ) from exc
    if vault_scope == "enterprise":
        assert isinstance(fm, EnterpriseFrontmatter)
        fm = append_audit_event(fm, actor or "unknown", "created", reason=None)
    return fm


def _frontmatter_to_yaml(fm: CommonFrontmatter) -> str:
    raw = fm.model_dump(mode="json")
    return yaml_dump_safe(raw)


def _write_note(
    path: Path,
    fm: CommonFrontmatter,
    body: str,
    vault: VaultLike,
    overwrite: bool,
) -> None:
    if path.exists() and not overwrite:
        raise DuplicateDocumentError(f"Document already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    yaml_str = _frontmatter_to_yaml(fm)
    full_md = "---\n" + yaml_str + "---\n\n" + body
    path.write_text(full_md, encoding="utf-8")
    try:
        rel_path = str(path.relative_to(vault.path))
    except ValueError:
        rel_path = str(path)
    indexer = getattr(vault, "index_file", None)
    if callable(indexer):
        try:
            indexer(rel_path)
        except Exception:  # pragma: no cover - defensive
            # Indexing failure must not abort the write.
            pass


# ---------------------------------------------------------------------------
# Generic canonical writer.
# ---------------------------------------------------------------------------


def _write_canonical(
    data: Any,
    doc_type: DocType,
    *,
    vault: VaultLike,
    vault_scope: str,
    project_id: str | None,
    actor: str | None,
    overwrite: bool,
    enforce_local_scope: bool = False,
) -> Path:
    if enforce_local_scope and vault_scope != "local":
        raise SchemaValidationError(
            f"{doc_type.value} is local-only; vault_scope must be 'local'"
        )
    if not getattr(data, "title", None):
        raise SchemaValidationError(f"{doc_type.value} requires a title")
    _require_enterprise_fields(data, vault_scope)

    route: RouteSpec = resolve_route(doc_type)

    # Render body via template using the data's dict form.
    template_vars = asdict(data)
    body = render_template(route.template_path.name, template_vars)

    fingerprint = compute_fingerprint(body)

    filename_ctx = _build_filename_context(data, doc_type, vault)
    fm = _build_frontmatter(
        data, doc_type, fingerprint, vault_scope, actor, filename_ctx
    )

    target = resolve_target_path(
        route, filename_ctx, vault.path, vault_scope, project_id
    )

    _write_note(target, fm, body, vault, overwrite)
    return target


# ---------------------------------------------------------------------------
# Public writers - 9 new functions, identical signature.
# ---------------------------------------------------------------------------


def write_adr_note(
    data: ADRData,
    *,
    vault: VaultLike,
    vault_scope: str = "local",
    project_id: str | None = None,
    actor: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Persist an ADR note canonically."""
    return _write_canonical(
        data, DocType.ADR,
        vault=vault, vault_scope=vault_scope,
        project_id=project_id, actor=actor, overwrite=overwrite,
    )


def write_decision_note(
    data: DecisionData,
    *,
    vault: VaultLike,
    vault_scope: str = "local",
    project_id: str | None = None,
    actor: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Persist a non-ADR DECISION note canonically."""
    return _write_canonical(
        data, DocType.DECISION,
        vault=vault, vault_scope=vault_scope,
        project_id=project_id, actor=actor, overwrite=overwrite,
    )


def write_incident_note(
    data: IncidentData,
    *,
    vault: VaultLike,
    vault_scope: str = "local",
    project_id: str | None = None,
    actor: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Persist an INCIDENT note canonically."""
    return _write_canonical(
        data, DocType.INCIDENT,
        vault=vault, vault_scope=vault_scope,
        project_id=project_id, actor=actor, overwrite=overwrite,
    )


def write_postmortem_note(
    data: PostmortemData,
    *,
    vault: VaultLike,
    vault_scope: str = "local",
    project_id: str | None = None,
    actor: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Persist a POSTMORTEM note canonically."""
    if not data.incident_path:
        raise SchemaValidationError("postmortem requires incident_path")
    if data.incident_number <= 0:
        raise SchemaValidationError("postmortem requires incident_number >= 1")
    return _write_canonical(
        data, DocType.POSTMORTEM,
        vault=vault, vault_scope=vault_scope,
        project_id=project_id, actor=actor, overwrite=overwrite,
    )


def write_runbook_note(
    data: RunbookData,
    *,
    vault: VaultLike,
    vault_scope: str = "local",
    project_id: str | None = None,
    actor: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Persist a RUNBOOK note canonically."""
    return _write_canonical(
        data, DocType.RUNBOOK,
        vault=vault, vault_scope=vault_scope,
        project_id=project_id, actor=actor, overwrite=overwrite,
    )


def write_architecture_note(
    data: ArchitectureData,
    *,
    vault: VaultLike,
    vault_scope: str = "local",
    project_id: str | None = None,
    actor: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Persist an ARCHITECTURE note canonically."""
    return _write_canonical(
        data, DocType.ARCHITECTURE,
        vault=vault, vault_scope=vault_scope,
        project_id=project_id, actor=actor, overwrite=overwrite,
    )


def write_changelog_note(
    data: ChangelogData,
    *,
    vault: VaultLike,
    vault_scope: str = "local",
    project_id: str | None = None,
    actor: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Persist a CHANGELOG entry canonically (one file per version)."""
    if not data.version:
        raise SchemaValidationError("changelog requires version")
    return _write_canonical(
        data, DocType.CHANGELOG,
        vault=vault, vault_scope=vault_scope,
        project_id=project_id, actor=actor, overwrite=overwrite,
    )


def write_handoff_note(
    data: HandoffData,
    *,
    vault: VaultLike,
    vault_scope: str = "local",
    project_id: str | None = None,
    actor: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Persist a HANDOFF note canonically.

    HANDOFF is local-only: vault_scope must be 'local'.
    """
    if not data.parent_session_id:
        raise SchemaValidationError("handoff requires parent_session_id")
    return _write_canonical(
        data, DocType.HANDOFF,
        vault=vault, vault_scope=vault_scope,
        project_id=project_id, actor=actor, overwrite=overwrite,
        enforce_local_scope=True,
    )


def write_glossary_entry(
    data: GlossaryEntryData,
    *,
    vault: VaultLike,
    vault_scope: str = "local",
    project_id: str | None = None,
    actor: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Persist a GLOSSARY entry canonically (one file per term)."""
    if not data.term:
        raise SchemaValidationError("glossary entry requires term")
    if not data.definition:
        raise SchemaValidationError("glossary entry requires definition")
    # Use term as title if title is empty.
    if not data.title:
        data.title = data.term
    return _write_canonical(
        data, DocType.GLOSSARY,
        vault=vault, vault_scope=vault_scope,
        project_id=project_id, actor=actor, overwrite=overwrite,
    )


# ---------------------------------------------------------------------------
# Canonical writers for the 3 legacy DocTypes (Fase 04).
# ---------------------------------------------------------------------------


def write_session_note_canonical(
    data: SessionData,
    *,
    vault: VaultLike,
    vault_scope: str = "local",
    project_id: str | None = None,
    actor: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Persist a SESSION note canonically (Fase 04 canonical writer)."""
    if not data.session_id:
        raise SchemaValidationError("session requires session_id")
    return _write_canonical(
        data, DocType.SESSION,
        vault=vault, vault_scope=vault_scope,
        project_id=project_id, actor=actor, overwrite=overwrite,
    )


def write_spec_note_canonical(
    data: SpecData,
    *,
    vault: VaultLike,
    vault_scope: str = "local",
    project_id: str | None = None,
    actor: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Persist a SPEC note canonically (Fase 04 canonical writer)."""
    return _write_canonical(
        data, DocType.SPEC,
        vault=vault, vault_scope=vault_scope,
        project_id=project_id, actor=actor, overwrite=overwrite,
    )


def write_hu_note(
    data: HUData,
    *,
    vault: VaultLike,
    vault_scope: str = "local",
    project_id: str | None = None,
    actor: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Persist an HU (work item) note canonically (Fase 04 canonical writer)."""
    if not data.external_id:
        raise SchemaValidationError("hu requires external_id")
    if not data.source:
        raise SchemaValidationError("hu requires source")
    return _write_canonical(
        data, DocType.HU,
        vault=vault, vault_scope=vault_scope,
        project_id=project_id, actor=actor, overwrite=overwrite,
    )


__all__ = [
    "VaultLike",
    "write_adr_note",
    "write_decision_note",
    "write_incident_note",
    "write_postmortem_note",
    "write_runbook_note",
    "write_architecture_note",
    "write_changelog_note",
    "write_handoff_note",
    "write_glossary_entry",
    # Canonical for legacy types (Fase 04):
    "write_session_note_canonical",
    "write_spec_note_canonical",
    "write_hu_note",
]
