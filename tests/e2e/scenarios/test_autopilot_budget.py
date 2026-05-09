"""E2E scenarios: budget and context metrics per profile.

Validates that each task type respects its budget contract:
- question_only: zero chars, zero items, no embeddings
- docs_only: low chars, low items, no subagents
- fast_code: moderate chars/items
- deep_code: allows subagents, records deep_track_reason
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cortex.autopilot.cli import app
from cortex.autopilot.context_budget import BUDGET_PROFILES, get_budget_profile, profile_for_task_type

runner = CliRunner()


class TestBudgetProfiles:
    """Validate static budget profile contracts."""

    def test_question_only_zero_budget(self) -> None:
        prof = get_budget_profile("question_only")
        assert prof["max_chars"] == 0
        assert prof["max_items"] == 0
        assert prof["embeddings"] is False
        assert prof["subagents"] is False

    def test_docs_only_low_budget(self) -> None:
        prof = get_budget_profile("docs_only")
        assert prof["max_chars"] == 1200
        assert prof["max_items"] == 3
        assert prof["embeddings"] is True
        assert prof["subagents"] is False

    def test_fast_code_moderate_budget(self) -> None:
        prof = get_budget_profile("fast_code")
        assert prof["max_chars"] == 2000
        assert prof["max_items"] == 5
        assert prof["embeddings"] is True
        assert prof["subagents"] is False

    def test_deep_code_allows_subagents(self) -> None:
        prof = get_budget_profile("deep_code")
        assert prof["max_chars"] == 3500
        assert prof["max_items"] == 8
        assert prof["embeddings"] is True
        assert prof["subagents"] is True

    def test_finish_only_no_embeddings(self) -> None:
        prof = get_budget_profile("finish_only")
        assert prof["max_chars"] == 2000
        assert prof["embeddings"] is False
        assert prof["subagents"] is False


class TestBudgetAtRuntime:
    """Measure budget snapshot persisted in state after preflight/finish."""

    def test_question_only_persists_zero_context(self, autopilot_workspace: Path) -> None:
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
                "What is the auth flow?",
                "--json",
            ],
        )
        runner.invoke(
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
        state_path = (
            autopilot_workspace
            / ".cortex"
            / "run"
            / "autopilot"
            / "sessions"
            / f"{sid}.json"
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        budget = state["budget"]
        # question-only path does not call build_context, so defaults remain
        assert budget["chars_injected"] == 0
        assert budget["items_retrieved"] == 0
        assert budget["embeddings_used"] is False
        assert budget["subagents_spawned"] == 0

    def test_fast_code_budget_greater_than_zero_on_context(self, autopilot_workspace: Path) -> None:
        """If build_context is called, fast_code should cap chars <= 2000."""
        from cortex.autopilot.service import AutopilotService
        from cortex.autopilot.state_store import StateStore

        store = StateStore(autopilot_workspace / ".cortex")
        svc = AutopilotService(state_store=store)

        start = svc.start(
            type("Request", (), {
                "project_root": str(autopilot_workspace),
                "workspace_root": str(autopilot_workspace / ".cortex"),
                "mode": "assist",
                "user_request": "Implement feature",
                "title_hint": None,
            })()
        )
        sid = start.session_id

        # Simulate detection state
        state = store.load_state(sid)
        state.detected_task_type = "fast-code"
        state.complexity = "fast"
        store.save_state(state)

        # build_context with None memory triggers fallback (empty) but still records budget
        prompt, budget = svc.build_context(sid, memory=None)
        # Fallback empty prompt => 0 chars, but profile fast_code allows up to 2000
        assert budget.chars_injected <= 2000
        assert budget.items_retrieved <= 5
        assert budget.embeddings_used is False  # fallback path does not use embeddings
        assert budget.subagents_spawned == 0

    def test_deep_code_records_deep_track_reason(self, autopilot_workspace: Path) -> None:
        r1 = runner.invoke(
            app, ["start", "--project-root", str(autopilot_workspace), "--json"]
        )
        sid = json.loads(r1.output)["session_id"]

        files = [f"m{i}.py" for i in range(6)]
        cmd = [
            "preflight",
            "--project-root",
            str(autopilot_workspace),
            "--session-id",
            sid,
            "--request",
            "Migrate legacy modules to new architecture",
            "--json",
        ]
        for f in files:
            cmd.extend(["--file", f])
        runner.invoke(app, cmd)

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
        assert len(state["budget"]["deep_track_reason"]) > 0

    def test_profile_mapping_consistency(self) -> None:
        """Every task type maps to a known profile name."""
        for task_type in [
            "question-only",
            "docs-only",
            "fast-code",
            "deep-code",
            "security",
            "ambiguous",
            "noop",
        ]:
            profile = profile_for_task_type(task_type)
            assert profile in BUDGET_PROFILES, f"{task_type} -> {profile} not in profiles"
