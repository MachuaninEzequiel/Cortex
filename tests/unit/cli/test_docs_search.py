"""Tests for ``cortex docs search`` CLI (Fase 13)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cortex.cli.docs_search import search as _search_cmd

runner = CliRunner()


@pytest.fixture
def fake_ctx():
    """Return a fake EnrichedContext suitable for ContextPresenter."""
    from cortex.models import EnrichedContext, EnrichedItem, WorkContext
    return EnrichedContext(
        work=WorkContext(source="manual", changed_files=[], keywords=["x"], search_queries=["x"]),
        items=[
            EnrichedItem(
                source="semantic", source_id="decisions/ADR-007.md",
                title="ADR-007", content="adopt ONNX",
                score=0.8, enriched_score=0.8, matched_by=["topic_search"],
                doc_type="adr", status="accepted", tags=["onnx"],
            ),
        ],
        total_items=1, total_chars=200,
    )


def _make_app(fake_ctx):
    import typer
    app = typer.Typer()

    # Adding a callback forces Typer to treat ``app`` as a command group
    # even with a single registered subcommand.
    @app.callback()
    def _main() -> None: ...

    app.command(name="search")(_search_cmd)

    def fake_build(_root):
        enricher = MagicMock()
        enricher.enrich = MagicMock(return_value=fake_ctx)
        return enricher

    return app, fake_build


def test_search_text_output(fake_ctx) -> None:
    app, fake_build = _make_app(fake_ctx)
    with patch("cortex.cli.docs_search._build_enricher", side_effect=fake_build):
        result = runner.invoke(app, ["search", "onnx"])
    assert result.exit_code == 0
    assert "ADR" in result.stdout
    assert "ADR-007" in result.stdout


def test_search_json_output(fake_ctx) -> None:
    import json
    app, fake_build = _make_app(fake_ctx)
    with patch("cortex.cli.docs_search._build_enricher", side_effect=fake_build):
        result = runner.invoke(app, ["search", "onnx", "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["items"][0]["doc_type"] == "adr"


def test_search_compact_output(fake_ctx) -> None:
    app, fake_build = _make_app(fake_ctx)
    with patch("cortex.cli.docs_search._build_enricher", side_effect=fake_build):
        result = runner.invoke(app, ["search", "onnx", "--format", "compact"])
    assert result.exit_code == 0
    assert "[ADR]" in result.stdout


def test_search_invalid_doc_type(fake_ctx) -> None:
    app, fake_build = _make_app(fake_ctx)
    with patch("cortex.cli.docs_search._build_enricher", side_effect=fake_build):
        result = runner.invoke(app, ["search", "x", "--doc-type", "bogus"])
    assert result.exit_code != 0


def test_search_invalid_scope(fake_ctx) -> None:
    app, fake_build = _make_app(fake_ctx)
    with patch("cortex.cli.docs_search._build_enricher", side_effect=fake_build):
        result = runner.invoke(app, ["search", "x", "--scope", "weird"])
    assert result.exit_code != 0


def test_search_invalid_format(fake_ctx) -> None:
    app, fake_build = _make_app(fake_ctx)
    with patch("cortex.cli.docs_search._build_enricher", side_effect=fake_build):
        result = runner.invoke(app, ["search", "x", "--format", "yaml"])
    assert result.exit_code != 0


def test_search_passes_filters_to_enricher(fake_ctx) -> None:
    captured: dict = {}

    def capturing_build(_root):
        enricher = MagicMock()

        def enrich(work, *, top_k=None, filters=None):
            captured["filters"] = filters
            captured["top_k"] = top_k
            return fake_ctx

        enricher.enrich = enrich
        return enricher

    app, _ = _make_app(fake_ctx)
    with patch("cortex.cli.docs_search._build_enricher", side_effect=capturing_build):
        result = runner.invoke(
            app, ["search", "deploy", "--doc-type", "runbook", "--max-age-days", "30",
                  "--scope", "local", "--tag", "ops"],
        )
    assert result.exit_code == 0
    f = captured["filters"]
    assert f.doc_types and f.doc_types[0].value == "runbook"
    assert f.max_age_days == 30
    assert f.vault_scope == "local"
    assert "ops" in f.tags_required
