"""Tests for the Phase-03 ``cortex autopilot`` Typer subapp (T3.4)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from cortex.autopilot.cli import app
from cortex.session.service import SessionService
from cortex.session.storage import SessionStorage


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def cortex_repo(tmp_path: Path) -> Path:
    """A tiny git repo with the bare workspace bones the CLI needs."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".cortex" / "sessions").mkdir(parents=True)
    (repo / "config.yaml").write_text("episodic: {}\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "i"], cwd=repo, check=True)
    return repo


def _open_session(repo: Path) -> str:
    """Open a session directly via SessionService so the CLI can adopt it."""
    storage = SessionStorage(repo / ".cortex" / "sessions")
    svc = SessionService(storage, repo)
    spec_dir = repo / "vault" / "specs"
    spec_dir.mkdir(parents=True, exist_ok=True)
    spec_path = spec_dir / "2026-05-16_demo.md"
    spec_path.write_text("# demo\n", encoding="utf-8")
    record = svc.open(
        spec_id="2026-05-16_demo",
        spec_path=spec_path,
        spec_summary="demo session",
    )
    return record.session_id


# ── start ────────────────────────────────────────────────────────────


class TestStart:
    def test_no_active_session_errors(self, runner: CliRunner, cortex_repo: Path) -> None:
        result = runner.invoke(
            app, ["start", "--project-root", str(cortex_repo), "--json"]
        )
        assert result.exit_code == 1
        assert "active session" in result.output.lower()

    def test_with_active_session_succeeds(self, runner: CliRunner, cortex_repo: Path) -> None:
        _open_session(cortex_repo)
        result = runner.invoke(
            app, ["start", "--project-root", str(cortex_repo), "--json"]
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["session_id"] == "2026-05-16_demo"
        assert payload["mode"] == "assist"

    def test_invalid_mode_exits_2(self, runner: CliRunner, cortex_repo: Path) -> None:
        result = runner.invoke(
            app,
            ["start", "--project-root", str(cortex_repo), "--mode", "hyperdrive"],
        )
        assert result.exit_code == 2


# ── preflight ───────────────────────────────────────────────────────


class TestPreflight:
    def test_outputs_detection(self, runner: CliRunner, cortex_repo: Path) -> None:
        result = runner.invoke(
            app,
            [
                "preflight",
                "--project-root",
                str(cortex_repo),
                "--request",
                "implement JWT refresh",
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert "task_type" in payload
        assert "confidence" in payload


# ── checkpoint ──────────────────────────────────────────────────────


class TestCheckpoint:
    def test_no_active_session_errors(self, runner: CliRunner, cortex_repo: Path) -> None:
        result = runner.invoke(
            app,
            [
                "checkpoint",
                "--project-root",
                str(cortex_repo),
                "--source",
                "manual",
                "--note",
                "nothing",
                "--json",
            ],
        )
        assert result.exit_code == 1

    def test_with_active_session(self, runner: CliRunner, cortex_repo: Path) -> None:
        _open_session(cortex_repo)
        result = runner.invoke(
            app,
            [
                "checkpoint",
                "--project-root",
                str(cortex_repo),
                "--source",
                "manual",
                "--note",
                "n1",
                "--artifact",
                "src/a.py",
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["checkpoints_count"] == 1


# ── finish ──────────────────────────────────────────────────────────


class TestFinish:
    def test_finish_without_auto_closes_session(
        self, runner: CliRunner, cortex_repo: Path
    ) -> None:
        _open_session(cortex_repo)
        result = runner.invoke(
            app,
            ["finish", "--project-root", str(cortex_repo), "--json"],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["status"] == "closed"
        assert payload["documented"] is False

    def test_handoff_intent(self, runner: CliRunner, cortex_repo: Path) -> None:
        _open_session(cortex_repo)
        result = runner.invoke(
            app,
            [
                "finish",
                "--project-root",
                str(cortex_repo),
                "--handoff",
                "--reason",
                "blocker",
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["status"] == "handoff"

    def test_handoff_and_abandon_mutually_exclusive(
        self, runner: CliRunner, cortex_repo: Path
    ) -> None:
        result = runner.invoke(
            app,
            [
                "finish",
                "--project-root",
                str(cortex_repo),
                "--handoff",
                "--abandon",
            ],
        )
        assert result.exit_code == 2


# ── status ──────────────────────────────────────────────────────────


class TestStatus:
    def test_no_active_session(self, runner: CliRunner, cortex_repo: Path) -> None:
        result = runner.invoke(
            app, ["status", "--project-root", str(cortex_repo), "--json"]
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["active"] is False

    def test_active_session(self, runner: CliRunner, cortex_repo: Path) -> None:
        _open_session(cortex_repo)
        result = runner.invoke(
            app, ["status", "--project-root", str(cortex_repo), "--json"]
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["active"] is True
        assert payload["session_id"] == "2026-05-16_demo"


# ── doctor ──────────────────────────────────────────────────────────


class TestDoctor:
    def test_returns_report(self, runner: CliRunner, cortex_repo: Path) -> None:
        result = runner.invoke(
            app, ["doctor", "--project-root", str(cortex_repo), "--json"]
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert "checks" in payload
        names = {c["name"] for c in payload["checks"]}
        assert {"config", "sessions_dir", "adapters", "last_finish"} <= names


# install / uninstall commands removed in Phase 04 cleanup — use
# ``cortex session hooks install --ide <name>`` (covered by
# tests/unit/cli/test_session_hooks_cli.py).


# Suppress noisy unused-import warnings.
_ = patch
_ = typer
