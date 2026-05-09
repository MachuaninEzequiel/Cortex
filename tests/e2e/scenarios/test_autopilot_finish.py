"""E2E scenarios: finish behaviour — safe draft, no duplicates, blocked policy.

These tests validate the ``finish --auto`` contract with real CLI-local
execution (``CliRunner``).  No agents, no network.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cortex.autopilot.cli import app

runner = CliRunner()


class TestFinishNoData:
    """Scenario 5 — Finish with no observed data must generate a safe draft."""

    def test_safe_draft_no_evidence(self, autopilot_workspace: Path) -> None:
        r1 = runner.invoke(
            app, ["start", "--project-root", str(autopilot_workspace), "--json"]
        )
        sid = json.loads(r1.output)["session_id"]

        r2 = runner.invoke(
            app,
            [
                "finish",
                "--project-root",
                str(autopilot_workspace),
                "--session-id",
                sid,
                "--auto",
                "--json",
            ],
        )
        assert r2.exit_code == 0, r2.output
        fin = json.loads(r2.output)
        assert fin["saved"] is True
        assert fin["status"] == "documented"
        # Draft confidence must be conservative when no data exists
        assert fin["draft_confidence"] == "auto-draft"
        # Warnings must flag the lack of observed data
        assert any(
            "No user request" in w or "incomplete" in w or "auto-draft" in w
            for w in fin["draft_warnings"]
        )

    def test_no_invented_files_or_tests(self, autopilot_workspace: Path) -> None:
        r1 = runner.invoke(
            app, ["start", "--project-root", str(autopilot_workspace), "--json"]
        )
        sid = json.loads(r1.output)["session_id"]

        r2 = runner.invoke(
            app,
            [
                "finish",
                "--project-root",
                str(autopilot_workspace),
                "--session-id",
                sid,
                "--auto",
                "--json",
            ],
        )
        fin = json.loads(r2.output)
        body_lower = json.dumps(fin).lower()
        # Must not claim tests passed or files were touched when none observed
        assert "tests pass" not in body_lower
        assert "build exitoso" not in body_lower
        assert "linter clean" not in body_lower


class TestFinishDuplicate:
    """Second finish must not duplicate the session note."""

    def test_no_duplicate_session_note(self, autopilot_workspace: Path) -> None:
        r1 = runner.invoke(
            app, ["start", "--project-root", str(autopilot_workspace), "--json"]
        )
        sid = json.loads(r1.output)["session_id"]

        runner.invoke(
            app,
            [
                "checkpoint",
                "--project-root",
                str(autopilot_workspace),
                "--session-id",
                sid,
                "--summary",
                "ck1",
                "--json",
            ],
        )

        r2 = runner.invoke(
            app,
            [
                "finish",
                "--project-root",
                str(autopilot_workspace),
                "--session-id",
                sid,
                "--auto",
                "--json",
            ],
        )
        fin1 = json.loads(r2.output)
        assert fin1["saved"] is True
        assert fin1["status"] == "documented"

        r3 = runner.invoke(
            app,
            [
                "finish",
                "--project-root",
                str(autopilot_workspace),
                "--session-id",
                sid,
                "--auto",
                "--json",
            ],
        )
        fin2 = json.loads(r3.output)
        assert fin2["saved"] is False
        assert fin2["status"] == "documented"
        # The CLI payload says "No draft generated" on duplicate; the underlying
        # event records "Session note already exists".  We verify the state file.
        state_path = (
            autopilot_workspace
            / ".cortex"
            / "run"
            / "autopilot"
            / "sessions"
            / f"{sid}.json"
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert state["session_note_path"] is not None


class TestFinishBlocked:
    """Scenario 6 — Tool failure proxy: blocked policy degrades with warning."""

    def test_blocked_generates_warning_draft(self, autopilot_workspace: Path) -> None:
        """AutoCheckpointPolicy blocks finish in autopilot mode with >5 changed files
        and no checkpoint.  The draft is generated but status stays ``finished``
        (not ``documented``), and a warning is emitted.
        """
        r1 = runner.invoke(
            app,
            [
                "start",
                "--project-root",
                str(autopilot_workspace),
                "--mode",
                "autopilot",
                "--json",
            ],
        )
        sid = json.loads(r1.output)["session_id"]

        # Preflight with many files changed but NO checkpoint
        files = [f"f{i}.py" for i in range(10)]
        cmd = [
            "preflight",
            "--project-root",
            str(autopilot_workspace),
            "--session-id",
            sid,
            "--request",
            "Big refactor",
            "--json",
        ]
        for f in files:
            cmd.extend(["--file", f])
        r2 = runner.invoke(app, cmd)
        assert r2.exit_code == 0, r2.output

        r3 = runner.invoke(
            app,
            [
                "finish",
                "--project-root",
                str(autopilot_workspace),
                "--session-id",
                sid,
                "--auto",
                "--json",
            ],
        )
        assert r3.exit_code == 0, r3.output
        fin = json.loads(r3.output)
        # Blocked by AutoCheckpointPolicy => not documented
        assert fin["status"] == "finished"
        assert fin["saved"] is False
        assert "draft_confidence" in fin
        # The policy block reason is stored in state.warnings, not in the draft.
        # Verify it persisted in the state file.
        state_path = (
            autopilot_workspace
            / ".cortex"
            / "run"
            / "autopilot"
            / "sessions"
            / f"{sid}.json"
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert any(
            "files changed without checkpoint" in w.lower()
            for w in state["warnings"]
        )

    def test_blocked_does_not_mark_documented(self, autopilot_workspace: Path) -> None:
        r1 = runner.invoke(
            app,
            [
                "start",
                "--project-root",
                str(autopilot_workspace),
                "--mode",
                "autopilot",
                "--json",
            ],
        )
        sid = json.loads(r1.output)["session_id"]

        files = [f"x{i}.py" for i in range(8)]
        cmd = [
            "preflight",
            "--project-root",
            str(autopilot_workspace),
            "--session-id",
            sid,
            "--request",
            "Migrate module",
            "--json",
        ]
        for f in files:
            cmd.extend(["--file", f])
        runner.invoke(app, cmd)

        r3 = runner.invoke(
            app,
            [
                "finish",
                "--project-root",
                str(autopilot_workspace),
                "--session-id",
                sid,
                "--auto",
                "--json",
            ],
        )
        fin = json.loads(r3.output)
        assert fin["status"] != "documented"
        # Must not invent success claims
        body = json.dumps(fin).lower()
        assert "verificado" not in body
        # Policy block reason persisted in state
        state_path = (
            autopilot_workspace
            / ".cortex"
            / "run"
            / "autopilot"
            / "sessions"
            / f"{sid}.json"
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert any("checkpoint" in w.lower() for w in state["warnings"])
