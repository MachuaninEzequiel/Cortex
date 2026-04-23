from __future__ import annotations

import json
from pathlib import Path

from cortex.ide import get_supported_ides
from cortex.ide.registry import get_adapter


def test_supported_ides_registry() -> None:
    ides = get_supported_ides()
    assert "opencode" in ides
    assert "cursor" in ides
    assert "vscode" in ides
    assert "windsurf" in ides
    assert "antigravity" in ides
    assert "hermes" in ides


def test_opencode_adapter_inject_profiles(monkeypatch, tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    
    # Mock home dir for the adapter to write to
    monkeypatch.setattr("cortex.ide.adapters.opencode.Path.home", staticmethod(lambda: tmp_path))

    adapter = get_adapter("opencode")
    prompts = {
        "cortex-sync": "Pre-flight prompt",
        "cortex-SDDwork": "Orchestrator prompt"
    }

    files = adapter.inject_profiles(project_root, prompts)

    config_path = tmp_path / ".config" / "opencode" / "opencode.json"
    assert config_path.exists()
    assert str(config_path) in files

    data = json.loads(config_path.read_text(encoding="utf-8"))

    # Assert basic structure
    assert "cortex-sync" in data["agent"]
    assert "cortex-SDDwork" in data["agent"]
    
    # Check that tools are correctly enabled
    assert data["agent"]["cortex-sync"]["tools"]["cortex_sync_ticket"] is True
    assert data["agent"]["cortex-sync"]["tools"]["write"] is False
    assert data["agent"]["cortex-SDDwork"]["tools"]["Task"] is True
    assert data["agent"]["cortex-SDDwork"]["tools"]["edit"] is True
    assert data["agent"]["cortex-SDDwork"]["tools"]["write"] is True

    # Check that the files were written
    skills_dir = tmp_path / ".config" / "opencode" / "skills"
    assert (skills_dir / "cortex-sync.md").read_text() == "Pre-flight prompt"
    assert (skills_dir / "cortex-SDDwork.md").read_text() == "Orchestrator prompt"


def test_cursor_adapter_inject_mcp(monkeypatch, tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    
    monkeypatch.setattr("cortex.ide.adapters.cursor.Path.home", staticmethod(lambda: tmp_path))

    adapter = get_adapter("cursor")
    files = adapter.inject_mcp(project_root)

    mcp_path = tmp_path / ".cursor" / "mcp.json"
    assert mcp_path.exists()
    assert str(mcp_path) in files

    data = json.loads(mcp_path.read_text(encoding="utf-8"))
    
    assert "cortex" in data["mcpServers"]
    assert data["mcpServers"]["cortex"]["command"] == "cortex"
    assert "mcp-server" in data["mcpServers"]["cortex"]["args"]
    assert data["mcpServers"]["cortex"]["env"]["PYTHONPATH"] == str(project_root)


def test_registry_accepts_common_aliases() -> None:
    assert get_adapter("claude").name == "claude_code"
    assert get_adapter("claude-desktop").name == "claude_desktop"
