"""Tests for cortex.autopilot.cli."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cortex.autopilot.cli import app

runner = CliRunner()


class TestStart:
    def test_start_default(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["start", "--project-root", str(tmp_path)])
        assert result.exit_code == 0
        assert "session_id" in result.output
        assert "status" in result.output

    def test_start_json(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["start", "--project-root", str(tmp_path), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "session_id" in data
        assert data["mode"] == "assist"
        assert data["status"] == "started"

    def test_start_with_mode(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app, ["start", "--project-root", str(tmp_path), "--mode", "autopilot", "--json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["mode"] == "autopilot"

    def test_start_with_request(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            [
                "start",
                "--project-root",
                str(tmp_path),
                "--request",
                "Fix login bug",
                "--json",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "session_id" in data


class TestPreflight:
    def test_preflight_without_session(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app, ["preflight", "--project-root", str(tmp_path), "--session-id", "nosuch", "--json"]
        )
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert "error" in data

    def test_preflight_success(self, tmp_path: Path) -> None:
        # Start a session first
        r1 = runner.invoke(app, ["start", "--project-root", str(tmp_path), "--json"])
        sid = json.loads(r1.output)["session_id"]

        r2 = runner.invoke(
            app,
            [
                "preflight",
                "--project-root",
                str(tmp_path),
                "--session-id",
                sid,
                "--request",
                "Implement new feature",
                "--file",
                "feat.py",
                "--json",
            ],
        )
        assert r2.exit_code == 0
        data = json.loads(r2.output)
        assert data["task_type"] == "fast-code"
        assert "can_proceed" in data
        assert "policy_decisions" in data


class TestCheckpoint:
    def test_checkpoint_without_session(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app, ["checkpoint", "--project-root", str(tmp_path), "--session-id", "bad", "--summary", "x", "--json"]
        )
        assert result.exit_code == 1

    def test_checkpoint_success(self, tmp_path: Path) -> None:
        r1 = runner.invoke(app, ["start", "--project-root", str(tmp_path), "--json"])
        sid = json.loads(r1.output)["session_id"]

        r2 = runner.invoke(
            app,
            [
                "checkpoint",
                "--project-root",
                str(tmp_path),
                "--session-id",
                sid,
                "--summary",
                "Added auth logic",
                "--file",
                "auth.py",
                "--verified",
                "--json",
            ],
        )
        assert r2.exit_code == 0
        data = json.loads(r2.output)
        assert data["checkpoints_count"] == 1
        assert data["status"] == "implementation_seen"


class TestFinish:
    def test_finish_without_session(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app, ["finish", "--project-root", str(tmp_path), "--session-id", "bad", "--json"]
        )
        assert result.exit_code == 1

    def test_finish_auto(self, tmp_path: Path) -> None:
        r1 = runner.invoke(app, ["start", "--project-root", str(tmp_path), "--json"])
        sid = json.loads(r1.output)["session_id"]

        r2 = runner.invoke(
            app,
            [
                "finish",
                "--project-root",
                str(tmp_path),
                "--session-id",
                sid,
                "--auto",
                "--json",
            ],
        )
        assert r2.exit_code == 0
        data = json.loads(r2.output)
        assert "status" in data
        assert "saved" in data
        # Should return draft info or reason
        assert "draft_title" in data or "reason" in data

    def test_finish_no_auto(self, tmp_path: Path) -> None:
        r1 = runner.invoke(app, ["start", "--project-root", str(tmp_path), "--json"])
        sid = json.loads(r1.output)["session_id"]

        r2 = runner.invoke(
            app,
            [
                "finish",
                "--project-root",
                str(tmp_path),
                "--session-id",
                sid,
                "--json",
            ],
        )
        assert r2.exit_code == 0
        data = json.loads(r2.output)
        assert data["saved"] is False


class TestStatus:
    def test_status_no_sessions(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["status", "--project-root", str(tmp_path), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["active"] is False

    def test_status_with_session(self, tmp_path: Path) -> None:
        r1 = runner.invoke(app, ["start", "--project-root", str(tmp_path), "--json"])
        sid = json.loads(r1.output)["session_id"]

        r2 = runner.invoke(
            app, ["status", "--project-root", str(tmp_path), "--session-id", sid, "--json"]
        )
        assert r2.exit_code == 0
        data = json.loads(r2.output)
        assert data["active"] is True
        assert data["session_id"] == sid


class TestDoctor:
    def test_doctor_no_modifications(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["doctor", "--project-root", str(tmp_path), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "checks" in data
        assert data["ok"] is True
        # Verify no files were created outside run/autopilot
        assert not (tmp_path / ".cortex" / "doctor_marker").exists()

    def test_doctor_text_output(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["doctor", "--project-root", str(tmp_path)])
        assert result.exit_code == 0
        assert "config" in result.output or "run_dir" in result.output
