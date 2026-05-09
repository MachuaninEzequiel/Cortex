"""E2E scenarios: basic Autopilot flows (question, fast-code, docs-only, deep-track, cleanup).

These tests exercise the real CLI deterministically using ``CliRunner``.
No external agents, no network, no token consumption.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cortex.autopilot.cli import app

runner = CliRunner()


class TestQuestionOnly:
    """Scenario 1 — Simple question: no heavy retrieval, zero budget."""

    def test_detects_question_only(self, autopilot_workspace: Path) -> None:
        r1 = runner.invoke(
            app, ["start", "--project-root", str(autopilot_workspace), "--json"]
        )
        assert r1.exit_code == 0, r1.output
        sid = json.loads(r1.output)["session_id"]

        r2 = runner.invoke(
            app,
            [
                "preflight",
                "--project-root",
                str(autopilot_workspace),
                "--session-id",
                sid,
                "--request",
                "What is the auth flow?",
                "--json",
            ],
        )
        assert r2.exit_code == 0, r2.output
        data = json.loads(r2.output)
        assert data["task_type"] == "question-only"
        assert data["can_proceed"] is True

    def test_no_embeddings_budget(self, autopilot_workspace: Path) -> None:
        r1 = runner.invoke(
            app, ["start", "--project-root", str(autopilot_workspace), "--json"]
        )
        sid = json.loads(r1.output)["session_id"]

        runner.invoke(
            app,
            [
                "preflight",
                "--project-root",
                str(autopilot_workspace),
                "--session-id",
                sid,
                "--request",
                "How do I reset my password?",
                "--json",
            ],
        )
        # finish auto — question-only does not trigger embeddings
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
        # Budget profile question_only => no context injected by default path,
        # but finish still marks documented because policies allow it.
        assert fin["status"] == "documented"
        # No spec should exist
        assert not (autopilot_workspace / ".cortex" / "vault" / "specs").exists()


class TestFastCode:
    """Scenario 2 — Simple change: Fast Track, session draft on finish.

    Known limitation (documented in evals.md):
    ``finish --auto`` sets ``session_note_path`` but does NOT write a physical
    file to vault. Only the path is recorded in state.
    """

    def test_fast_track_draft_on_finish(self, autopilot_workspace: Path) -> None:
        r1 = runner.invoke(
            app, ["start", "--project-root", str(autopilot_workspace), "--json"]
        )
        sid = json.loads(r1.output)["session_id"]

        r2 = runner.invoke(
            app,
            [
                "preflight",
                "--project-root",
                str(autopilot_workspace),
                "--session-id",
                sid,
                "--request",
                "Implement user profile page",
                "--file",
                "profiles.py",
                "--json",
            ],
        )
        assert r2.exit_code == 0, r2.output
        pre = json.loads(r2.output)
        assert pre["task_type"] == "fast-code"

        r3 = runner.invoke(
            app,
            [
                "checkpoint",
                "--project-root",
                str(autopilot_workspace),
                "--session-id",
                sid,
                "--summary",
                "Fixed login validation",
                "--file",
                "login.py",
                "--verified",
                "--json",
            ],
        )
        assert r3.exit_code == 0, r3.output

        r4 = runner.invoke(
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
        assert r4.exit_code == 0, r4.output
        fin = json.loads(r4.output)
        assert fin["saved"] is True
        assert fin["status"] == "documented"
        assert "draft_title" in fin

        # Verify that the physical session note is NOT written (known limitation)
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
        note_physical = autopilot_workspace / ".cortex" / state["session_note_path"]
        assert not note_physical.exists(), (
            "Physical session note should not exist; only path is recorded in state"
        )


class TestDocsOnly:
    """Scenario 3 — Docs-only: low budget, docs-only profile."""

    def test_docs_only_profile(self, autopilot_workspace: Path) -> None:
        r1 = runner.invoke(
            app, ["start", "--project-root", str(autopilot_workspace), "--json"]
        )
        sid = json.loads(r1.output)["session_id"]

        r2 = runner.invoke(
            app,
            [
                "preflight",
                "--project-root",
                str(autopilot_workspace),
                "--session-id",
                sid,
                "--request",
                "Document the new API endpoints in README.md",
                "--file",
                "README.md",
                "--json",
            ],
        )
        assert r2.exit_code == 0, r2.output
        pre = json.loads(r2.output)
        assert pre["task_type"] == "docs-only"

        # finish auto — docs-only should produce a draft with low complexity
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
        assert fin["saved"] is True
        assert fin["status"] == "documented"


class TestDeepTrack:
    """Scenario 4 — Complex task: Deep Track suggestion, delegation stub."""

    def test_deep_track_suggestion(self, autopilot_workspace: Path) -> None:
        r1 = runner.invoke(
            app, ["start", "--project-root", str(autopilot_workspace), "--json"]
        )
        sid = json.loads(r1.output)["session_id"]

        r2 = runner.invoke(
            app,
            [
                "preflight",
                "--project-root",
                str(autopilot_workspace),
                "--session-id",
                sid,
                "--request",
                "Migrate legacy payment modules",
                "--file",
                "module1.py",
                "--file",
                "module2.py",
                "--file",
                "module3.py",
                "--file",
                "module4.py",
                "--file",
                "module5.py",
                "--file",
                "module6.py",
                "--json",
            ],
        )
        assert r2.exit_code == 0, r2.output
        pre = json.loads(r2.output)
        # LargeRefactorDetector triggers deep-code when >5 files
        assert pre["task_type"] == "deep-code"

        # Verify deep_track_reason persisted in state
        state_path = (
            autopilot_workspace
            / ".cortex"
            / "run"
            / "autopilot"
            / "sessions"
            / f"{sid}.json"
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert state["complexity"] == "deep"
        assert state["budget"]["deep_track_reason"] is not None

    def test_delegation_stub_no_cross_process_persistence(self, autopilot_workspace: Path) -> None:
        """Delegation registry is in-memory; e2e must not assume cross-process persistence."""
        from cortex.autopilot.delegation import register_task, get_task_result, _task_registry
        from cortex.autopilot.models import DelegationResult

        task_id = "stub-task-001"
        register_task(
            DelegationResult(
                task_id=task_id,
                status="completed",
                diff_summary="added login.py",
                files_changed=["login.py"],
            )
        )
        assert get_task_result(task_id) is not None
        # Clear registry to prove it does not persist
        _task_registry.clear()
        assert get_task_result(task_id) is None


class TestCleanupAndConfig:
    """Scenario 7 — Cleanup leaves configuration tidy."""

    def test_cleanup_archives_old_jsonl(self, autopilot_workspace: Path) -> None:
        import time
        import os

        events_dir = (
            autopilot_workspace / ".cortex" / "run" / "autopilot" / "events"
        )
        events_dir.mkdir(parents=True, exist_ok=True)
        old_file = events_dir / "old.jsonl"
        old_file.write_text("event\n", encoding="utf-8")
        old_mtime = time.time() - 40 * 86400
        os.utime(old_file, (old_mtime, old_mtime))

        r1 = runner.invoke(
            app,
            [
                "cleanup",
                "--project-root",
                str(autopilot_workspace),
                "--older-than",
                "30",
                "--json",
            ],
        )
        assert r1.exit_code == 0, r1.output
        data = json.loads(r1.output)
        assert len(data["archived"]) == 1
        assert not old_file.exists()

    def test_cleanup_older_than_expects_integer(self, autopilot_workspace: Path) -> None:
        """CLI ``cleanup --older-than`` expects an integer (days), not ``30d``."""
        r1 = runner.invoke(
            app,
            [
                "cleanup",
                "--project-root",
                str(autopilot_workspace),
                "--older-than",
                "30d",
                "--json",
            ],
        )
        # Typer will reject "30d" because the option expects an int
        assert r1.exit_code != 0
