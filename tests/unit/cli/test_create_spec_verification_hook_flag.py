"""Tests for the ``--verification-hook`` flag of ``cortex create-spec`` (T1.2)."""

from __future__ import annotations

import pytest

from cortex.cli.main import _parse_verification_hooks


class TestParseVerificationHooks:
    def test_empty_input_returns_empty(self) -> None:
        assert _parse_verification_hooks([]) == []

    def test_single_hook_with_name_and_command(self) -> None:
        out = _parse_verification_hooks(["name=tests;command=pytest tests/auth/"])
        assert out == [{"name": "tests", "command": "pytest tests/auth/"}]

    def test_multiple_hooks(self) -> None:
        out = _parse_verification_hooks(
            [
                "name=tests;command=pytest",
                "name=lint;command=ruff check .;required=false",
            ]
        )
        assert len(out) == 2
        assert out[0]["name"] == "tests"
        assert out[1]["required"] is False

    def test_required_true_coerced(self) -> None:
        out = _parse_verification_hooks(
            ["name=x;command=y;required=true"]
        )
        assert out[0]["required"] is True

    def test_required_yes_coerced(self) -> None:
        out = _parse_verification_hooks(["name=x;command=y;required=YES"])
        assert out[0]["required"] is True

    def test_timeout_seconds_coerced_to_int(self) -> None:
        out = _parse_verification_hooks(["name=x;command=y;timeout_seconds=60"])
        assert out[0]["timeout_seconds"] == 60

    def test_invalid_timeout_seconds_exits(self) -> None:
        import typer

        with pytest.raises(typer.Exit):
            _parse_verification_hooks(["name=x;command=y;timeout_seconds=abc"])

    def test_unknown_key_exits(self) -> None:
        import typer

        with pytest.raises(typer.Exit):
            _parse_verification_hooks(["name=x;bogus=y"])

    def test_pair_without_equals_exits(self) -> None:
        import typer

        with pytest.raises(typer.Exit):
            _parse_verification_hooks(["name=x;invalidpair"])

    def test_blank_entries_skipped(self) -> None:
        out = _parse_verification_hooks(["", "  "])
        assert out == []

    def test_command_with_spaces_preserved(self) -> None:
        out = _parse_verification_hooks(
            ["name=tests;command=pytest tests/ -v --tb=short"]
        )
        assert out[0]["command"] == "pytest tests/ -v --tb=short"
