"""Tests for the canonical writers exposed via ``cortex.documentation``.

After Item #10 the legacy-shaped wrappers were removed. Consumers and tests
now build the dataclass and call the canonical writer directly.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from cortex.documentation import (
    parse_frontmatter_lenient,
    write_hu_note,
    write_session_note_canonical,
    write_spec_note_canonical,
)
from cortex.documentation.data import HUData, SessionData, SpecData
from cortex.workitems.models import TrackedItem, WorkItemKind, WorkItemSource


class _PathOnlyVault:
    """Minimal VaultLike for tests (no semantic indexing)."""

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def path(self) -> Path:
        return self._root

    def index_file(self, relative_path: str) -> bool:
        return False


def _session_data(**overrides: object) -> SessionData:
    base = dict(
        title="Implement Release 2 flow",
        tags=["session", "release-2"],
        status="completed",
        session_id=uuid.uuid4().hex[:12],
        spec_summary="Replace cortex-work with cortex-SDDwork.",
        changes_made=["Added orchestrator prompt", "Added documenter flow"],
        files_touched=["cortex/ide_installer.py", "cortex/mcp_server.py"],
        key_decisions=["Make cortex-documenter mandatory"],
        next_steps=["Add more ADR coverage"],
    )
    base.update(overrides)
    return SessionData(**base)  # type: ignore[arg-type]


def test_write_session_note_creates_session_file(tmp_path: Path) -> None:
    path = write_session_note_canonical(_session_data(), vault=_PathOnlyVault(tmp_path))

    assert path.exists()
    assert path.parent.name == "sessions"
    content = path.read_text(encoding="utf-8")
    fm = parse_frontmatter_lenient(path)
    assert fm["title"] == "Implement Release 2 flow"
    assert fm["doc_type"] == "session"
    assert "Replace cortex-work with cortex-SDDwork." in content
    assert "cortex/ide_installer.py" in content


def test_write_spec_note_creates_spec_file(tmp_path: Path) -> None:
    data = SpecData(
        title="Release 2 subagent architecture",
        tags=["spec", "architecture"],
        status="draft",
        goal="Install sync + SDDwork + documenter workflow.",
        requirements=["Support subagents", "Preserve Cortex isolation"],
        files_in_scope=["cortex/setup/orchestrator.py"],
        constraints=["Do not use external memory tools"],
        acceptance_criteria=["cortex-SDDwork is installed", "documenter is mandatory"],
    )
    path = write_spec_note_canonical(data, vault=_PathOnlyVault(tmp_path))

    assert path.exists()
    assert path.parent.name == "specs"
    fm = parse_frontmatter_lenient(path)
    assert fm["title"] == "Release 2 subagent architecture"
    assert fm["doc_type"] == "spec"
    content = path.read_text(encoding="utf-8")
    assert "Preserve Cortex isolation" in content
    assert "documenter is mandatory" in content


# ---------------------------------------------------------------------------
# Tripartita Refinada - Plan 07 §4: cascade save_session(handoff=True) e2e
# ---------------------------------------------------------------------------


def test_write_session_note_handoff_mode_writes_handoff_status(tmp_path: Path) -> None:
    """Con ``status='handoff'`` y tag ``handoff``, las 4 secciones Tripartita
    Refinada deben renderizarse cuando las listas son no vacias.
    """
    data = _session_data(
        title="Tripartita Refinada - Plan 07 cierre",
        tags=["session", "release", "handoff"],
        status="handoff",
        spec_summary="Cierre del bloque Tripartita Refinada con bump 0.5.0",
        changes_made=["MCP tools handoff", "agents canonical"],
        files_touched=["cortex/handoff.py"],
        key_decisions=["Bump 0.5.0"],
        next_steps=["Reunion adopters"],
        blockers=["Smoke manual de los 4 IDEs pendiente del usuario"],
        verified_state=["Suite global verde", "MCP tools registrados"],
        unverified_claims=["Performance overhead < 10% no medido en este ciclo"],
        suggested_skills=["cortex-documenter para review de la bitacora"],
    )
    path = write_session_note_canonical(data, vault=_PathOnlyVault(tmp_path))

    assert path.exists()
    fm = parse_frontmatter_lenient(path)
    assert fm["status"] == "handoff"
    tags = fm["tags"]
    assert "session" in tags
    assert "release" in tags
    assert "handoff" in tags
    assert tags.count("handoff") == 1

    content = path.read_text(encoding="utf-8")
    assert "## Verified State" in content
    assert "## Unverified Claims" in content
    assert "## Blockers" in content
    assert "## Suggested Skills" in content
    assert "Suite global verde" in content
    assert "Smoke manual de los 4 IDEs pendiente del usuario" in content


def test_write_session_note_handoff_false_omits_new_sections(tmp_path: Path) -> None:
    """Negative control: cuando status='completed' las 4 secciones nuevas
    NO aparecen aunque las listas esten vacias."""
    data = _session_data(
        title="Normal session",
        tags=["session"],
        status="completed",
        spec_summary="x",
        changes_made=[],
        files_touched=[],
        key_decisions=[],
        next_steps=[],
    )
    path = write_session_note_canonical(data, vault=_PathOnlyVault(tmp_path))
    content = path.read_text(encoding="utf-8")
    fm = parse_frontmatter_lenient(path)
    assert fm["status"] == "completed"
    assert "## Verified State" not in content
    assert "## Unverified Claims" not in content
    assert "## Blockers" not in content
    assert "## Suggested Skills" not in content


def test_write_session_note_handoff_with_empty_lists_skips_sections(tmp_path: Path) -> None:
    """status='handoff' pero con listas vacias -> status cambia pero no aparecen
    secciones. Solo listas no vacias materializan secciones."""
    data = _session_data(
        title="Empty handoff",
        tags=["session", "handoff"],
        status="handoff",
        spec_summary="x",
        changes_made=[],
        files_touched=[],
        key_decisions=[],
        next_steps=[],
    )
    path = write_session_note_canonical(data, vault=_PathOnlyVault(tmp_path))
    content = path.read_text(encoding="utf-8")
    fm = parse_frontmatter_lenient(path)
    assert fm["status"] == "handoff"
    assert "## Verified State" not in content
    assert "## Blockers" not in content


def test_write_tracked_item_note_creates_hu_file(tmp_path: Path) -> None:
    item = TrackedItem(
        id="PROJ-123",
        external_id="PROJ-123",
        source=WorkItemSource.JIRA,
        kind=WorkItemKind.STORY,
        title="Import Jira story",
        description="Read-only import for the current ticket.",
        acceptance_criteria=["Ticket is persisted locally"],
        status="In Progress",
        labels=["jira", "story"],
    )
    data = HUData(
        title=f"{item.id}: {item.title}",
        tags=["hu", item.source.value, item.kind.value, *item.labels],
        status="in-progress" if item.status == "In Progress" else (item.status or "backlog"),
        external_id=item.id,
        source=item.source.value,
        kind=item.kind.value,
        description=item.description,
        acceptance_criteria=list(item.acceptance_criteria),
    )
    path = write_hu_note(data, vault=_PathOnlyVault(tmp_path))

    assert path.exists()
    assert path.parent.name == "hu"
    fm = parse_frontmatter_lenient(path)
    assert fm["external_id"] == "PROJ-123"
    assert fm["doc_type"] == "hu"
    assert fm["source"] == "jira"
    assert fm["kind"] == "story"
    content = path.read_text(encoding="utf-8")
    assert "Read-only import for the current ticket." in content
    assert "Ticket is persisted locally" in content
