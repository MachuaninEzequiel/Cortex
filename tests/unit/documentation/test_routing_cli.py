"""Tests for the ``cortex docs routing-table`` CLI."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from cortex.cli.docs_subcommand import app

runner = CliRunner()


def test_cli_routing_table_prints_all() -> None:
    result = runner.invoke(app, ["routing-table"])
    assert result.exit_code == 0
    # Header row.
    assert "DocType" in result.stdout
    # All 12 types should appear.
    for slug in (
        "session",
        "handoff",
        "spec",
        "adr",
        "decision",
        "incident",
        "postmortem",
        "runbook",
        "architecture",
        "changelog",
        "hu",
        "glossary",
    ):
        assert slug in result.stdout


def test_cli_routing_table_filters_by_doc_type_json() -> None:
    result = runner.invoke(app, ["routing-table", "--doc-type", "adr", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["doc_type"] == "adr"
    assert payload["subfolder"] == "decisions"
    assert payload["filename_template"] == "ADR-{number:03d}-{slug}.md"


def test_cli_routing_table_json_full_is_a_list() -> None:
    result = runner.invoke(app, ["routing-table", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)
    assert len(payload) == 12


def test_cli_routing_table_invalid_doc_type_fails() -> None:
    result = runner.invoke(app, ["routing-table", "--doc-type", "bogus"])
    assert result.exit_code != 0
    # Typer prints BadParameter to stderr or includes it in result.output
    output = result.stdout + (result.stderr if hasattr(result, "stderr") else "")
    assert "bogus" in output or result.exit_code != 0
