from __future__ import annotations

from pathlib import Path

from cortex.enterprise.reporting import EnterpriseReportingService


def _write_minimal_project(tmp_path: Path) -> None:
    (tmp_path / ".memory" / "chroma").mkdir(parents=True)
    (tmp_path / "vault").mkdir()
    (tmp_path / "config.yaml").write_text(
        "episodic:\n"
        "  persist_dir: .memory/chroma\n"
        "  collection_name: cortex_episodic\n"
        "  embedding_model: all-MiniLM-L6-v2\n"
        "  embedding_backend: onnx\n"
        "semantic:\n"
        "  vault_path: vault\n",
        encoding="utf-8",
    )
    (tmp_path / "vault" / "specs").mkdir()
    (tmp_path / "vault" / "specs" / "spec.md").write_text(
        "---\n"
        "title: Example Spec\n"
        "date: 2026-04-29\n"
        "tags: [spec]\n"
        "---\n\n"
        "# Spec\n\n"
        "Hello\n",
        encoding="utf-8",
    )


def _write_enterprise_org(tmp_path: Path) -> None:
    org_dir = tmp_path / ".cortex"
    org_dir.mkdir(parents=True, exist_ok=True)
    (org_dir / "org.yaml").write_text(
        "schema_version: 1\n"
        "organization:\n"
        "  name: Example Org\n"
        "  profile: small-company\n"
        "memory:\n"
        "  mode: layered\n"
        "  enterprise_vault_path: vault-enterprise\n"
        "  enterprise_memory_path: .memory/enterprise/chroma\n"
        "  enterprise_semantic_enabled: true\n"
        "  enterprise_episodic_enabled: false\n"
        "  project_memory_mode: isolated\n"
        "  branch_isolation_enabled: false\n"
        "  retrieval_default_scope: local\n"
        "  retrieval_local_weight: 1.0\n"
        "  retrieval_enterprise_weight: 1.0\n"
        "promotion:\n"
        "  enabled: true\n"
        "  allowed_doc_types: [spec, decision, runbook, hu, incident]\n"
        "  require_review: true\n"
        "  default_targets: [enterprise_vault]\n"
        "governance:\n"
        "  git_policy: balanced\n"
        "  ci_profile: advisory\n"
        "  version_sessions_in_git: false\n"
        "integration:\n"
        "  github_actions_enabled: true\n"
        "  webgraph_workspace_enabled: true\n"
        "  ide_profiles: []\n",
        encoding="utf-8",
    )
    ent = tmp_path / "vault-enterprise"
    ent.mkdir()
    (ent / "README.md").write_text(
        "---\n"
        "title: Enterprise Vault\n"
        "date: 2026-04-29\n"
        "tags: [enterprise]\n"
        "---\n\n"
        "# Enterprise\n",
        encoding="utf-8",
    )


def test_memory_report_local_only(tmp_path: Path) -> None:
    _write_minimal_project(tmp_path)
    service = EnterpriseReportingService.from_project_root(tmp_path)
    report = service.build_memory_report(scope="local")

    assert report.project_root.endswith(str(tmp_path).replace("\\", "/")) or str(tmp_path) in report.project_root
    assert any(s.scope == "local" for s in report.sources)
    assert not any(s.scope == "enterprise" for s in report.sources)


def test_memory_report_includes_enterprise_and_promotion(tmp_path: Path) -> None:
    _write_minimal_project(tmp_path)
    _write_enterprise_org(tmp_path)
    service = EnterpriseReportingService.from_project_root(tmp_path)
    report = service.build_memory_report(scope="all")

    assert report.enterprise_enabled is True
    assert any(s.scope == "local" for s in report.sources)
    assert any(s.scope == "enterprise" for s in report.sources)
    assert report.promotion.enabled is True
    assert report.promotion.candidates_discovered >= 1
