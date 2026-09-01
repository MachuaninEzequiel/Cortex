from __future__ import annotations

from unittest.mock import MagicMock

from typer.testing import CliRunner

from cortex.cli.main import app
from cortex.models import RetrievalResult

runner = CliRunner()


def _patch_enricher(monkeypatch, capturado: dict) -> None:
    """B3/B4: --scope enterprise/all va por el path estructural con filtros."""

    class FakeEnricher:
        def __init__(self, **kwargs: object) -> None:
            pass

        def enrich(self, work, *, top_k=None, filters=None):  # noqa: ANN001
            capturado["filters"] = filters
            from cortex.models import EnrichedContext, WorkContext

            return EnrichedContext(
                work=WorkContext(source="manual", changed_files=[], keywords=[], search_queries=[]),
                items=[], total_searches=0, total_raw_hits=0,
                total_items=0, total_chars=0, within_budget=True,
            )

    monkeypatch.setattr(
        "cortex.cli.main._load_memory", lambda: MagicMock(episodic=None, semantic=None)
    )
    monkeypatch.setattr("cortex.context_enricher.enricher.ContextEnricher", FakeEnricher)


def test_cli_search_scope_local_e2e(monkeypatch) -> None:
    class DummyMemory:
        def retrieve(self, query, top_k, cross_branch, scope, project_id=None):  # noqa: ANN001
            assert scope == "local"
            return RetrievalResult(query=query)

    monkeypatch.setattr("cortex.cli.main._load_memory", lambda: DummyMemory())
    result = runner.invoke(app, ["search", "auth", "--scope", "local"])
    assert result.exit_code == 0


def test_cli_search_scope_enterprise_e2e(monkeypatch) -> None:
    capturado: dict = {}
    _patch_enricher(monkeypatch, capturado)
    result = runner.invoke(app, ["search", "auth", "--scope", "enterprise"])
    assert result.exit_code == 0
    assert capturado["filters"].vault_scope == "enterprise"


def test_cli_search_scope_all_e2e(monkeypatch) -> None:
    capturado: dict = {}
    _patch_enricher(monkeypatch, capturado)
    result = runner.invoke(app, ["search", "auth", "--scope", "all"])
    assert result.exit_code == 0
    assert capturado["filters"].vault_scope == "all"


def test_cli_search_enterprise_without_org_returns_error(monkeypatch) -> None:
    """Sin org.yaml el store enterprise subyacente debe fallar ruidoso."""
    capturado: dict = {}
    _patch_enricher(monkeypatch, capturado)

    class FakeEnricherOrg:
        def __init__(self, **kwargs: object) -> None:
            pass

        def enrich(self, work, *, top_k=None, filters=None):  # noqa: ANN001
            raise ValueError("Enterprise retrieval scope requires .cortex/org.yaml.")

    monkeypatch.setattr(
        "cortex.context_enricher.enricher.ContextEnricher", FakeEnricherOrg
    )
    resultado = runner.invoke(app, ["search", "auth", "--scope", "enterprise"])
    assert resultado.exception is not None or resultado.exit_code != 0
