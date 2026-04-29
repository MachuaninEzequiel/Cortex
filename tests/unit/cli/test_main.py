from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from cortex.cli.main import app
from cortex.models import RetrievalResult, UnifiedHit

runner = CliRunner()


def test_install_skills_uses_dest_argument(monkeypatch, tmp_path: Path) -> None:
    called: dict[str, Path] = {}

    def fake_install_skills(target_path: Path) -> list[str]:
        called["target_path"] = target_path
        return ["obsidian-cli"]

    monkeypatch.setattr("cortex.skills.install_skills", fake_install_skills)

    result = runner.invoke(app, ["install-skills", "--dest", str(tmp_path)])

    assert result.exit_code == 0
    assert called["target_path"] == tmp_path
    assert str(tmp_path) in result.stdout


def test_install_ide_specific_target_uses_adapter_layer(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_inject(ide_name: str, project_root: Path | None = None) -> list[str]:
        called["ide_name"] = ide_name
        called["project_root"] = project_root
        return ["ok"]

    monkeypatch.setattr("cortex.ide.inject", fake_inject)

    result = runner.invoke(app, ["install-ide", "--ide", "cursor"])

    assert result.exit_code == 0
    assert called["ide_name"] == "cursor"
    assert called["project_root"] == Path.cwd()


def test_inject_uses_new_ide_module(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_inject(ide_name: str, project_root: Path | None = None) -> list[str]:
        called["ide_name"] = ide_name
        called["project_root"] = project_root
        return ["ok"]

    monkeypatch.setattr("cortex.ide.inject", fake_inject)

    result = runner.invoke(app, ["inject", "--ide", "cursor"])

    assert result.exit_code == 0
    assert called["ide_name"] == "cursor"
    assert called["project_root"] == Path.cwd()


def test_validate_docs_command_writes_report(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "note.md").write_text(
        "---\n"
        'title: "Valid Note"\n'
        "date: 2026-04-26\n"
        "tags: [docs]\n"
        "---\n\n"
        "# Valid Note\n",
        encoding="utf-8",
    )
    output = tmp_path / "doc-validation.json"

    result = runner.invoke(app, ["validate-docs", "--vault", str(vault), "--output", str(output)])

    assert result.exit_code == 0
    assert output.exists()
    assert '"error_count": 0' in output.read_text(encoding="utf-8")


def test_doctor_command_fails_when_config_is_missing(tmp_path: Path) -> None:
    result = runner.invoke(app, ["doctor", "--project-root", str(tmp_path)])

    assert result.exit_code == 1
    assert "config_yaml" in result.output


def test_doctor_enterprise_scope_fails_when_org_config_is_missing(tmp_path: Path) -> None:
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
    (tmp_path / "vault").mkdir()
    (tmp_path / ".memory" / "chroma").mkdir(parents=True)

    result = runner.invoke(
        app,
        ["doctor", "--project-root", str(tmp_path), "--scope", "enterprise"],
    )

    assert result.exit_code == 1
    assert "enterprise_config" in result.output


def test_org_config_command_prints_resolved_topology(tmp_path: Path) -> None:
    org_dir = tmp_path / ".cortex"
    org_dir.mkdir(parents=True)
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
    (tmp_path / "vault-enterprise").mkdir()

    result = runner.invoke(app, ["org-config", "--project-root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Example Org" in result.output
    assert "Topology:" in result.output


def test_search_scope_is_forwarded_to_retrieve(monkeypatch) -> None:
    class DummyMemory:
        def retrieve(self, query, top_k, cross_branch, scope, project_id=None):  # noqa: ANN001
            assert query == "hello"
            assert top_k == 3
            assert cross_branch is False
            assert scope == "enterprise"
            assert project_id is None
            return RetrievalResult(query="hello")

    monkeypatch.setattr("cortex.cli.main._load_memory", lambda: DummyMemory())
    result = runner.invoke(app, ["search", "hello", "--top-k", "3", "--scope", "enterprise"])
    assert result.exit_code == 0


def test_search_rejects_invalid_scope(monkeypatch) -> None:
    class DummyMemory:
        def retrieve(self, query, top_k, cross_branch, scope):  # noqa: ANN001
            return RetrievalResult(query=query)

    monkeypatch.setattr("cortex.cli.main._load_memory", lambda: DummyMemory())
    result = runner.invoke(app, ["search", "hello", "--scope", "bad-scope"])
    assert result.exit_code == 1
    assert "Invalid --scope value" in result.output


def test_search_show_scores_prints_scope_details(monkeypatch) -> None:
    class DummyMemory:
        def retrieve(self, query, top_k, cross_branch, scope, project_id=None):  # noqa: ANN001
            return RetrievalResult(
                query=query,
                unified_hits=[
                    UnifiedHit(
                        source="semantic",
                        score=0.42,
                        metadata={"scope": "enterprise", "project_id": "acme-org"},
                    )
                ],
                source_breakdown={"enterprise": 1},
            )

    monkeypatch.setattr("cortex.cli.main._load_memory", lambda: DummyMemory())
    result = runner.invoke(app, ["search", "hello", "--show-scores", "--scope", "all"])
    assert result.exit_code == 0
    assert "scope=enterprise" in result.output
    assert "Source breakdown" in result.output


def test_search_json_includes_source_breakdown(monkeypatch) -> None:
    class DummyMemory:
        def retrieve(self, query, top_k, cross_branch, scope, project_id=None):  # noqa: ANN001
            return RetrievalResult(
                query=query,
                source_breakdown={"local": 1, "enterprise": 2},
            )

    monkeypatch.setattr("cortex.cli.main._load_memory", lambda: DummyMemory())
    result = runner.invoke(app, ["search", "hello", "--json", "--scope", "all"])
    assert result.exit_code == 0
    assert '"source_breakdown"' in result.output


def test_search_without_scope_passes_none(monkeypatch) -> None:
    class DummyMemory:
        def retrieve(self, query, top_k, cross_branch, scope, project_id=None):  # noqa: ANN001
            assert scope is None
            assert project_id is None
            return RetrievalResult(query=query)

    monkeypatch.setattr("cortex.cli.main._load_memory", lambda: DummyMemory())
    result = runner.invoke(app, ["search", "hello"])
    assert result.exit_code == 0


def test_search_passes_project_id_filter(monkeypatch) -> None:
    class DummyMemory:
        def retrieve(self, query, top_k, cross_branch, scope, project_id):  # noqa: ANN001
            assert project_id == "acme-project"
            return RetrievalResult(query=query)

    monkeypatch.setattr("cortex.cli.main._load_memory", lambda: DummyMemory())
    result = runner.invoke(app, ["search", "hello", "--project-id", "acme-project"])
    assert result.exit_code == 0


def test_setup_enterprise_non_interactive_requires_input() -> None:
    result = runner.invoke(app, ["setup", "enterprise", "--non-interactive"])
    assert result.exit_code == 1
    assert "requires --preset or --org-config" in result.output


def test_setup_enterprise_with_preset_invokes_enterprise_mode(monkeypatch) -> None:
    called: dict[str, object] = {}

    class DummyOrchestrator:
        def run(self, **kwargs):  # noqa: ANN003
            called.update(kwargs)
            return {"created": [], "skipped": [], "warnings": []}

    monkeypatch.setattr("cortex.setup.orchestrator.SetupOrchestrator", DummyOrchestrator)
    result = runner.invoke(
        app,
        ["setup", "enterprise", "--preset", "small-company", "--non-interactive", "--json"],
    )

    assert result.exit_code == 0
    assert str(called.get("mode")) == "SetupMode.ENTERPRISE"
    assert called.get("enterprise_profile") == "small-company"


def test_memory_report_json_outputs_payload(tmp_path: Path) -> None:
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
    result = runner.invoke(app, ["memory-report", "--project-root", str(tmp_path), "--json"])
    assert result.exit_code == 0
    assert '"project_root"' in result.output
