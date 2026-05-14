"""cortex.documentation._legacy_shims - Backwards-compatible wrappers.

The 3 writers ``write_session_note``, ``write_spec_note`` and
``write_tracked_item_note`` retained their original Fase 0 signatures (with
``vault_path: str | Path`` and many keyword arguments) for downstream
consumers (``cortex.services.session_service``,
``cortex.services.spec_service``, ``cortex.workitems.service``,
``tests/unit/test_documentation.py``).

This module re-creates those signatures on top of the canonical writers
introduced in Fase 03/04. The shims build the dataclass, then delegate.

Fase 12 will deprecate these shims once the consumers migrate to the
canonical signatures.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, UTC
from pathlib import Path
from typing import TYPE_CHECKING

from cortex.documentation.data import HUData, SessionData, SpecData
from cortex.documentation.writers import (
    write_hu_note,
    write_session_note_canonical,
    write_spec_note_canonical,
)

if TYPE_CHECKING:
    from cortex.workitems.models import TrackedItem


class _PathOnlyVault:
    """Minimal VaultLike that wraps a bare path (no indexing).

    Legacy callers pass a vault directory string, not a VaultReader.
    """

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def path(self) -> Path:
        return self._root

    def index_file(self, relative_path: str) -> bool:  # pragma: no cover
        # Legacy callers indexed separately via VaultReader; the shim
        # intentionally does not re-index here.
        return False


def write_session_note(
    vault_path: str | Path,
    *,
    title: str,
    spec_summary: str,
    changes_made: list[str] | None = None,
    files_touched: list[str] | None = None,
    key_decisions: list[str] | None = None,
    next_steps: list[str] | None = None,
    tags: list[str] | None = None,
    note_date: date | None = None,
    handoff: bool = False,
    blockers: list[str] | None = None,
    verified_state: list[str] | None = None,
    unverified_claims: list[str] | None = None,
    suggested_skills: list[str] | None = None,
    cortex_telemetry: dict | None = None,
) -> Path:
    """Legacy-shaped wrapper around the canonical session writer.

    Mirrors the original Fase 0 signature so ``cortex.services.session_service``
    and similar consumers keep working without changes.

    The canonical writer requires ``session_id``; the shim generates a 12-char
    hex id when the caller doesn't provide one (legacy behavior).

    Fase 05 adds the optional ``cortex_telemetry`` block which is embedded in
    the session frontmatter so adopters can audit retrieval quality.
    """
    final_tags = ["session"] + list(tags or [])
    if handoff and "handoff" not in final_tags:
        final_tags.append("handoff")

    status = "handoff" if handoff else "completed"

    data = SessionData(
        title=title,
        tags=final_tags,
        status=status,
        session_id=uuid.uuid4().hex[:12],
        spec_summary=spec_summary or "",
        changes_made=list(changes_made or []),
        files_touched=list(files_touched or []),
        key_decisions=list(key_decisions or []),
        next_steps=list(next_steps or []),
        verified_state=list(verified_state or []),
        unverified_claims=list(unverified_claims or []),
        blockers=list(blockers or []),
        suggested_skills=list(suggested_skills or []),
        cortex_telemetry=cortex_telemetry,
    )
    vault = _PathOnlyVault(Path(vault_path))
    return write_session_note_canonical(data, vault=vault)


def write_spec_note(
    vault_path: str | Path,
    *,
    title: str,
    goal: str,
    requirements: list[str] | None = None,
    files_in_scope: list[str] | None = None,
    constraints: list[str] | None = None,
    acceptance_criteria: list[str] | None = None,
    tags: list[str] | None = None,
    note_date: date | None = None,
) -> Path:
    """Legacy-shaped wrapper around the canonical spec writer."""
    final_tags = ["spec"] + list(tags or [])
    data = SpecData(
        title=title,
        tags=final_tags,
        status="draft",
        goal=goal or "",
        requirements=list(requirements or []),
        files_in_scope=list(files_in_scope or []),
        constraints=list(constraints or []),
        acceptance_criteria=list(acceptance_criteria or []),
    )
    vault = _PathOnlyVault(Path(vault_path))
    return write_spec_note_canonical(data, vault=vault)


def write_tracked_item_note(
    vault_path: str | Path,
    *,
    item: "TrackedItem",
    note_date: date | None = None,
) -> Path:
    """Legacy-shaped wrapper around the canonical HU writer.

    Translates a ``TrackedItem`` model into an ``HUData`` dataclass.
    """
    final_tags = ["hu", item.source.value, item.kind.value] + list(item.labels)
    title = f"{item.id}: {item.title}"
    legacy_status = item.status or "imported"
    # Map legacy "imported" to canonical "backlog".
    canonical_status_map = {
        "imported": "backlog",
        "in_progress": "in-progress",
    }
    status = canonical_status_map.get(legacy_status, legacy_status)

    synced_at: datetime | None = None
    if item.sync_timestamp:
        synced_at = item.sync_timestamp
        if synced_at.tzinfo is None:
            synced_at = synced_at.replace(tzinfo=UTC)

    data = HUData(
        title=title,
        tags=final_tags,
        status=status,
        external_id=item.id,
        source=item.source.value,
        kind=item.kind.value,
        description=item.description or "",
        acceptance_criteria=list(item.acceptance_criteria or []),
        assignee=item.assignee,
        external_url=item.external_url,
        synced_at=synced_at,
    )
    vault = _PathOnlyVault(Path(vault_path))
    return write_hu_note(data, vault=vault)


__all__ = [
    "write_session_note",
    "write_spec_note",
    "write_tracked_item_note",
]
