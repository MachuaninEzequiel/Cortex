"""cortex.enterprise.promotion_doctype - DocType-aware promotion (Fase 10).

The legacy ``knowledge_promotion.py`` treats every promotable note the
same: copy + inject frontmatter. The canonical-documentation initiative
introduces three promotion modes (driven by ``RouteSpec.promotion_mode``):

    - ``as-is``           Copy the body unchanged.
    - ``summarize``       Synthesize a compact knowledge digest from the
                          source body (used for SESSION notes).
    - ``review-required`` Copy but set status='draft' so a reviewer must
                          approve before the doc goes ``published``.

This module provides ``promote_note_doctype_aware`` which is the entry
point the new pipeline calls. It does not replace
``KnowledgePromotionService`` — for now both coexist, and the new function
is opt-in.

The function is intentionally side-effect-free at the filesystem level
when ``dry_run=True``, so callers (CLI, tests) can preview the operation.
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from cortex.documentation.common import (
    compute_fingerprint,
    parse_frontmatter_lenient,
    split_frontmatter_and_body,
    yaml_dump_safe,
)
from cortex.documentation.doc_type import DocType
from cortex.documentation.errors import RoutingError
from cortex.documentation.routing import RouteSpec, resolve_route
from cortex.enterprise.governance import (
    ADMIN_TEAM,
    GovernancePermissionError,
    assert_can_promote,
)
from cortex.enterprise.models import EnterpriseOrgConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PromotionResult:
    """Outcome of a DocType-aware promotion call."""

    source_path: Path
    target_path: Path
    doc_type: DocType
    promotion_mode: str
    summarized: bool
    fingerprint: str
    requires_review: bool


class PromotionError(RuntimeError):
    """Raised when a DocType-aware promotion cannot proceed."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def promote_note_doctype_aware(
    source_path: Path,
    *,
    enterprise_vault_root: Path,
    org: EnterpriseOrgConfig,
    project_id: str,
    actor: str,
    reason: str | None = None,
    dry_run: bool = False,
) -> PromotionResult:
    """Promote ``source_path`` into ``enterprise_vault_root`` honouring
    the DocType's ``promotion_mode``.

    Steps:
        1. Validate actor + team permissions via ``governance``.
        2. Parse frontmatter, resolve DocType.
        3. Lookup ``RouteSpec``; refuse if ``promotable=False``.
        4. Resolve target path under ``enterprise_vault_root``.
        5. Apply the promotion_mode transformation (``as-is`` /
           ``summarize`` / ``review-required``).
        6. Inject the EnterpriseFrontmatter governance fields (owner,
           team, classification, retention_days, audit_trail).
        7. Write to target (or skip in dry-run).
    """
    assert_can_promote(actor, org)

    if not source_path.exists():
        raise PromotionError(f"source not found: {source_path}")

    fm, body = _read_note(source_path)
    if not fm:
        raise PromotionError(f"missing or invalid frontmatter: {source_path}")
    raw_doc_type = fm.get("doc_type")
    if not isinstance(raw_doc_type, str):
        raise PromotionError(f"source has no doc_type: {source_path}")
    try:
        doc_type = DocType(raw_doc_type)
    except ValueError as exc:
        raise PromotionError(
            f"unknown doc_type {raw_doc_type!r} in {source_path}"
        ) from exc

    try:
        route = resolve_route(doc_type)
    except RoutingError as exc:
        raise PromotionError(str(exc)) from exc

    if not route.promotable:
        raise PromotionError(
            f"{doc_type.value!r} is not promotable (promotable=False in RouteSpec)"
        )

    # Incident severity gate: skip low-severity unless severity is given as
    # one of {medium, high, critical}.
    if doc_type is DocType.INCIDENT:
        sev = fm.get("severity")
        if sev == "low":
            raise PromotionError(
                "INCIDENT with severity=low is not promoted (gate by Fase 10)"
            )

    target_path = _resolve_target(route, source_path, fm, enterprise_vault_root, project_id)

    summarized = False
    new_body = body
    new_status = fm.get("status")
    if route.promotion_mode == "summarize":
        new_body = _summarize_session(fm, body)
        summarized = True
        if doc_type is DocType.SESSION:
            new_status = "completed"
    elif route.promotion_mode == "review-required":
        new_status = "draft"
    # ``as-is`` keeps both untouched.

    fingerprint = compute_fingerprint(new_body)
    new_fm = _build_enterprise_frontmatter(
        fm=fm,
        body_fingerprint=fingerprint,
        org=org,
        project_id=project_id,
        actor=actor,
        reason=reason,
        new_status=new_status,
        promotion_mode=route.promotion_mode,
    )

    if not dry_run:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(
            "---\n" + yaml_dump_safe(new_fm) + "---\n\n" + new_body,
            encoding="utf-8",
        )

    return PromotionResult(
        source_path=source_path,
        target_path=target_path,
        doc_type=doc_type,
        promotion_mode=route.promotion_mode,
        summarized=summarized,
        fingerprint=fingerprint,
        requires_review=route.requires_review_before_publish,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_note(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_text(encoding="utf-8")
    fm_yaml, body = split_frontmatter_and_body(raw)
    if not fm_yaml:
        return {}, body
    try:
        fm = yaml.safe_load(fm_yaml) or {}
    except yaml.YAMLError:
        fm = {}
    if not isinstance(fm, dict):
        fm = {}
    return fm, body


def _resolve_target(
    route: RouteSpec,
    source_path: Path,
    fm: dict[str, Any],
    enterprise_vault_root: Path,
    project_id: str,
) -> Path:
    """Pick the enterprise destination preserving the doc identity.

    Reuses the same filename as the source so promotion is idempotent.
    """
    if not route.enterprise_subfolder:
        raise PromotionError(
            f"{route.doc_type.value!r} has no enterprise_subfolder configured"
        )
    subfolder = route.enterprise_subfolder.format(project_id=project_id)
    return enterprise_vault_root / subfolder / source_path.name


def _build_enterprise_frontmatter(
    *,
    fm: dict[str, Any],
    body_fingerprint: str,
    org: EnterpriseOrgConfig,
    project_id: str,
    actor: str,
    reason: str | None,
    new_status: str | None,
    promotion_mode: str,
) -> dict[str, Any]:
    """Compose the enterprise frontmatter dict ready for ``yaml_dump_safe``.

    Pydantic ``EnterpriseFrontmatter`` validation happens later when a
    consumer reads the file; here we focus on producing a complete
    structured dict.
    """
    now = datetime.now(UTC).isoformat()
    out: dict[str, Any] = {
        "schema_version": int(fm.get("schema_version") or 1),
        "doc_type": fm["doc_type"],
        "title": fm.get("title") or "(untitled)",
        "created_at": fm.get("created_at") or now,
        "updated_at": now,
        "tags": list(fm.get("tags") or []),
        "status": new_status or fm.get("status") or "",
        "links": list(fm.get("links") or []),
        "vault_scope": "enterprise",
        "fingerprint": body_fingerprint,
    }
    # Enterprise governance fields.
    out["owner"] = fm.get("owner") or actor
    out["team"] = (
        fm.get("team")
        or (org.teams[0].id if org.teams else ADMIN_TEAM)
    )
    out["classification"] = (
        fm.get("classification") or "internal"
    )
    # retention_days: prefer explicit override, else default by doc_type.
    if "retention_days" in fm and isinstance(fm["retention_days"], int):
        out["retention_days"] = int(fm["retention_days"])
    else:
        out["retention_days"] = org.retention_defaults.for_doc_type(
            fm.get("doc_type") or ""
        )

    # Preserve any type-specific extra fields that came on the source.
    _KNOWN = {
        "schema_version", "doc_type", "title", "created_at", "updated_at",
        "tags", "status", "links", "vault_scope", "fingerprint",
        "owner", "team", "classification", "retention_days", "audit_trail",
    }
    for key, value in fm.items():
        if key not in _KNOWN:
            out[key] = value

    # Audit trail: preserve + append "promoted" event.
    existing_trail = list(fm.get("audit_trail") or [])
    existing_trail.append({
        "actor": actor,
        "action": "promoted",
        "timestamp": now,
        "reason": reason,
        "promotion_mode": promotion_mode,
    })
    out["audit_trail"] = existing_trail
    return out


_SESSION_INTRO = (
    "**Promoted session digest.** Full session lives at the source path."
)


def _summarize_session(fm: dict[str, Any], body: str) -> str:
    """Generate a compact digest from a SESSION body.

    Keeps the high-signal sections: Key Decisions, Verified State.
    """
    sections = _split_sections(body)
    parts: list[str] = [_SESSION_INTRO]
    for header in ("Key Decisions", "Verified State"):
        block = sections.get(header)
        if block:
            parts.append(f"\n## {header}\n\n{block.strip()}")
    title = fm.get("title") or "Session"
    return f"# {title}\n\n" + "\n".join(parts).strip() + "\n"


_H2_HEADER_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def _split_sections(body: str) -> dict[str, str]:
    """Split a markdown body into ``{section_title: section_body}`` by H2."""
    matches = list(_H2_HEADER_RE.finditer(body))
    out: dict[str, str] = {}
    for i, m in enumerate(matches):
        section_start = m.end()
        section_end = matches[i + 1].start() if (i + 1) < len(matches) else len(body)
        out[m.group(1).strip()] = body[section_start:section_end].strip()
    return out


__all__ = [
    "PromotionError",
    "PromotionResult",
    "promote_note_doctype_aware",
]
