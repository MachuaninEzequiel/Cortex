from __future__ import annotations

from pathlib import Path

from cortex.documentation import write_session_note, write_spec_note, write_tracked_item_note
from cortex.workitems.models import TrackedItem, WorkItemKind, WorkItemSource


def test_write_session_note_creates_session_file(tmp_path: Path) -> None:
    path = write_session_note(
        tmp_path,
        title="Implement Release 2 flow",
        spec_summary="Replace cortex-work with cortex-SDDwork.",
        changes_made=["Added orchestrator prompt", "Added documenter flow"],
        files_touched=["cortex/ide_installer.py", "cortex/mcp_server.py"],
        key_decisions=["Make cortex-documenter mandatory"],
        next_steps=["Add more ADR coverage"],
        tags=["release-2"],
    )

    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "Session: Implement Release 2 flow" in content
    assert "Replace cortex-work with cortex-SDDwork." in content
    assert "cortex/ide_installer.py" in content


def test_write_spec_note_creates_spec_file(tmp_path: Path) -> None:
    path = write_spec_note(
        tmp_path,
        title="Release 2 subagent architecture",
        goal="Install sync + SDDwork + documenter workflow.",
        requirements=["Support subagents", "Preserve Cortex isolation"],
        files_in_scope=["cortex/setup/orchestrator.py"],
        constraints=["Do not use external memory tools"],
        acceptance_criteria=["cortex-SDDwork is installed", "documenter is mandatory"],
        tags=["architecture"],
    )

    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "Specification: Release 2 subagent architecture" in content
    assert "Preserve Cortex isolation" in content
    assert "documenter is mandatory" in content


# ---------------------------------------------------------------------------
# Tripartita Refinada — Plan 07 §4: cascade save_session(handoff=True) e2e
# ---------------------------------------------------------------------------


def test_write_session_note_handoff_mode_writes_handoff_status(tmp_path: Path) -> None:
    """Plan 07 §4 — when ``handoff=True``, the materialized session note
    must carry ``status: handoff`` in its frontmatter and the ``handoff``
    tag (idempotently, not duplicated). This test cuts the cascade at the
    last layer so it exercises real frontmatter rendering on disk
    instead of mock kwargs.
    """
    path = write_session_note(
        tmp_path,
        title="Tripartita Refinada — Plan 07 cierre",
        spec_summary="Cierre del bloque Tripartita Refinada con bump 0.5.0",
        changes_made=["MCP tools handoff", "agents canonical"],
        files_touched=["cortex/handoff.py"],
        key_decisions=["Bump 0.5.0"],
        next_steps=["Reunión adopters"],
        tags=["release"],
        handoff=True,
        blockers=["Smoke manual de los 4 IDEs pendiente del usuario"],
        verified_state=["Suite global verde", "MCP tools registrados"],
        unverified_claims=["Performance overhead < 10% no medido en este ciclo"],
        suggested_skills=["cortex-documenter para review de la bitácora"],
    )

    assert path.exists()
    content = path.read_text(encoding="utf-8")
    # Frontmatter status must be 'handoff', not the default 'generated'.
    assert "status: handoff" in content
    # 'handoff' tag must appear once in the tags list.
    assert "tags: [session, release, handoff]" in content or (
        "handoff" in content and content.count(", handoff]") + content.count(", handoff,") == 1
    )
    # The 4 new sections must be emitted because we passed non-empty lists.
    assert "## Verified State" in content
    assert "## Unverified Claims" in content
    assert "## Blockers" in content
    assert "## Suggested Skills" in content
    # Body content rendered.
    assert "Suite global verde" in content
    assert "Smoke manual de los 4 IDEs pendiente del usuario" in content


def test_write_session_note_handoff_false_omits_new_sections(tmp_path: Path) -> None:
    """Negative control: when handoff=False (default) the 4 new sections
    do NOT appear, even if you pass empty lists. This guarantees the
    Tripartita Refinada additions are scoped to handoff mode."""
    path = write_session_note(
        tmp_path,
        title="Normal session",
        spec_summary="x",
    )
    content = path.read_text(encoding="utf-8")
    assert "status: generated" in content
    assert "## Verified State" not in content
    assert "## Unverified Claims" not in content
    assert "## Blockers" not in content
    assert "## Suggested Skills" not in content


def test_write_session_note_handoff_with_empty_lists_skips_sections(tmp_path: Path) -> None:
    """handoff=True but with no blockers/verified/etc → status changes
    but no sections appear. Only non-empty lists materialize sections."""
    path = write_session_note(
        tmp_path,
        title="Empty handoff",
        spec_summary="x",
        handoff=True,
    )
    content = path.read_text(encoding="utf-8")
    assert "status: handoff" in content
    assert "## Verified State" not in content
    assert "## Blockers" not in content


def test_write_tracked_item_note_creates_hu_file(tmp_path: Path) -> None:
    path = write_tracked_item_note(
        tmp_path,
        item=TrackedItem(
            id="PROJ-123",
            external_id="PROJ-123",
            source=WorkItemSource.JIRA,
            kind=WorkItemKind.STORY,
            title="Import Jira story",
            description="Read-only import for the current ticket.",
            acceptance_criteria=["Ticket is persisted locally"],
            status="In Progress",
            labels=["jira", "story"],
        ),
    )

    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert 'external_id: "PROJ-123"' in content
    assert "# PROJ-123: Import Jira story" in content
    assert "Ticket is persisted locally" in content
