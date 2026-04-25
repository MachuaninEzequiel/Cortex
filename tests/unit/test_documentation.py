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
