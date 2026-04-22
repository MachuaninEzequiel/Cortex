from __future__ import annotations

import json
from pathlib import Path

from cortex.ide_installer import install_opencode_profile


def test_install_opencode_profile_writes_tools_map(monkeypatch, tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    (project_root / ".cortex" / "skills").mkdir(parents=True, exist_ok=True)
    (project_root / ".cortex" / "subagents").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("cortex.ide_installer._find_cortex_project_root", lambda: project_root)
    monkeypatch.setattr("cortex.ide_installer.get_opencode_mcp_definition", lambda: {"cortex": {"enabled": True}})
    monkeypatch.setattr("cortex.ide_installer.Path.home", staticmethod(lambda: tmp_path))

    install_opencode_profile()

    config_path = tmp_path / ".config" / "opencode" / "opencode.json"
    data = json.loads(config_path.read_text(encoding="utf-8"))

    assert data["agent"]["cortex-sync"]["tools"]["cortex_sync_ticket"] is True
    assert data["agent"]["cortex-sync"]["tools"]["write"] is False
    assert data["agent"]["cortex-SDDwork"]["tools"]["cortex_delegate_batch"] is True
    assert data["agent"]["cortex-SDDwork"]["tools"]["edit"] is False
