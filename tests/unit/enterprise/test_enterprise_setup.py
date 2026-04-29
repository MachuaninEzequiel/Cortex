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


def test_setup_pipeline_creates_enterprise_governance_workflow(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(SetupOrchestrator, "_check_vault_pipeline_interactive", lambda self: None)
    monkeypatch.setattr(SetupOrchestrator, "_create_config", lambda self: None)
    monkeypatch.setattr(SetupOrchestrator, "_create_enterprise_org_config", lambda self: None)
    monkeypatch.setattr(SetupOrchestrator, "_create_enterprise_vault", lambda self: None)
    monkeypatch.setattr(SetupOrchestrator, "_create_devsecdocops_script", lambda self: None)

    orchestrator = SetupOrchestrator(root=tmp_path)
    summary = orchestrator.run(mode=SetupMode.PIPELINE)

    expected = ".github/workflows/ci-enterprise-governance.yml"
    assert expected in summary["created"] or (tmp_path / expected).exists()
    wf = tmp_path / ".github" / "workflows" / "ci-enterprise-governance.yml"
    assert wf.exists()
    text = wf.read_text(encoding="utf-8")
    assert "CI - Enterprise Governance" in text
    assert "cortex promote-knowledge" in text
    assert "cortex sync-enterprise-vault" in text


def test_setup_enterprise_dry_run_does_not_write_files(tmp_path: Path) -> None:
    orchestrator = SetupOrchestrator(root=tmp_path)
    summary = orchestrator.run(mode=SetupMode.ENTERPRISE, dry_run=True)

    assert any(item.endswith("(dry-run)") for item in summary["created"])
    assert not (tmp_path / ".cortex" / "org.yaml").exists()
    assert not (tmp_path / ".github" / "workflows").exists()
