from __future__ import annotations

from pathlib import Path

from cortex.setup.orchestrator import SetupMode, SetupOrchestrator


def test_setup_agent_creates_enterprise_org_config_and_vault(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(SetupOrchestrator, "_install_skills", lambda self: None)
    monkeypatch.setattr(SetupOrchestrator, "_init_memory", lambda self: None)
    monkeypatch.setattr(SetupOrchestrator, "_install_ide", lambda self: None)

    orchestrator = SetupOrchestrator(root=tmp_path)
    summary = orchestrator.run(mode=SetupMode.AGENT)

    assert ".cortex/org.yaml" in summary["created"]
    assert (tmp_path / ".cortex" / "org.yaml").exists()
    assert (tmp_path / "vault-enterprise" / "README.md").exists()
    assert (tmp_path / "vault-enterprise" / "runbooks").exists()
