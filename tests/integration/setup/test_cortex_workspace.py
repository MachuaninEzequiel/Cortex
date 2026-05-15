from __future__ import annotations

from pathlib import Path

from cortex.setup.cortex_workspace import ensure_cortex_workspace, workspace_file_map


def test_ensure_cortex_workspace_creates_release2_files(tmp_path: Path) -> None:
    result = ensure_cortex_workspace(tmp_path)

    assert ".cortex/system-prompt.md" in result["created"]
    assert ".cortex/skills/cortex-sync.md" in result["created"]
    assert ".cortex/skills/cortex-SDDwork.md" in result["created"]
    assert ".cortex/subagents/cortex-documenter.md" in result["created"]
    assert (tmp_path / ".cortex" / "subagents" / "cortex-code-explorer.md").exists()


def test_ensure_cortex_workspace_skips_existing_files(tmp_path: Path) -> None:
    existing = tmp_path / ".cortex" / "skills"
    existing.mkdir(parents=True, exist_ok=True)
    sync_path = existing / "cortex-sync.md"
    sync_path.write_text("custom", encoding="utf-8")

    result = ensure_cortex_workspace(tmp_path)

    assert ".cortex/skills/cortex-sync.md" in result["skipped"]
    assert sync_path.read_text(encoding="utf-8") == "custom"


def test_release2_workspace_prompts_require_sync_and_track_routing() -> None:
    files = workspace_file_map()

    assert "cortex_sync_ticket" in files[".cortex/skills/cortex-sync.md"]
    assert "FAST TRACK" in files[".cortex/skills/cortex-SDDwork.md"]
    assert "DEEP TRACK" in files[".cortex/skills/cortex-SDDwork.md"]
    # Tras Fase 5 plan multi-IDE & MCP hardening (2026-05-15): la skill
    # debe describir mecanismos NATIVOS de delegacion por IDE (Task tool
    # en Claude Code, mode: subagent en opencode, etc.), NO el viejo
    # `cortex_delegate_task` MCP que fue eliminado.
    sddwork_content = files[".cortex/skills/cortex-SDDwork.md"]
    assert "cortex_delegate_task" not in sddwork_content
    assert "Mecanismos de delegacion" in sddwork_content
    assert "Task" in sddwork_content  # native Task tool reference
