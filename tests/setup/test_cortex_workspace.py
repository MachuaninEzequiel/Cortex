from __future__ import annotations

from pathlib import Path

from cortex.setup.cortex_workspace import ensure_cortex_workspace


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
