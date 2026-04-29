from __future__ import annotations

from typer.testing import CliRunner

from cortex.cli.main import app
from cortex.models import RetrievalResult

runner = CliRunner()


def test_cli_search_scope_local_e2e(monkeypatch) -> None:
    class DummyMemory:
        def retrieve(self, query, top_k, cross_branch, scope, project_id=None):  # noqa: ANN001
            assert scope == "local"
            return RetrievalResult(query=query)

    monkeypatch.setattr("cortex.cli.main._load_memory", lambda: DummyMemory())
    result = runner.invoke(app, ["search", "auth", "--scope", "local"])
    assert result.exit_code == 0


def test_cli_search_scope_enterprise_e2e(monkeypatch) -> None:
    class DummyMemory:
        def retrieve(self, query, top_k, cross_branch, scope, project_id=None):  # noqa: ANN001
            assert scope == "enterprise"
            return RetrievalResult(query=query)

    monkeypatch.setattr("cortex.cli.main._load_memory", lambda: DummyMemory())
    result = runner.invoke(app, ["search", "auth", "--scope", "enterprise"])
    assert result.exit_code == 0


def test_cli_search_scope_all_e2e(monkeypatch) -> None:
    class DummyMemory:
        def retrieve(self, query, top_k, cross_branch, scope, project_id=None):  # noqa: ANN001
            assert scope == "all"
            return RetrievalResult(query=query)

    monkeypatch.setattr("cortex.cli.main._load_memory", lambda: DummyMemory())
    result = runner.invoke(app, ["search", "auth", "--scope", "all"])
    assert result.exit_code == 0


def test_cli_search_enterprise_without_org_returns_error(monkeypatch) -> None:
    class DummyMemory:
        def retrieve(self, query, top_k, cross_branch, scope, project_id=None):  # noqa: ANN001
            raise ValueError("Enterprise retrieval scope requires .cortex/org.yaml.")

    monkeypatch.setattr("cortex.cli.main._load_memory", lambda: DummyMemory())
    result = runner.invoke(app, ["search", "auth", "--scope", "enterprise"])
    assert result.exit_code == 1
    assert "org.yaml" in result.output
