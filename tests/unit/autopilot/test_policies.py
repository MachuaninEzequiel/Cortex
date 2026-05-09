"""Tests for cortex.autopilot.policies."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from cortex.autopilot.models import AutopilotCheckpoint, AutopilotSessionState, PolicyDecision
from cortex.autopilot.policies.auto_checkpoint import AutoCheckpointPolicy
from cortex.autopilot.policies.base import evaluate_policies, most_restrictive
from cortex.autopilot.policies.default import (
    BudgetPolicy,
    DocumentationRequiredPolicy,
    HumanApprovalPolicy,
    SpecRequiredPolicy,
)


def _make_state(**kwargs: object) -> AutopilotSessionState:
    defaults = dict(
        project_root="/repo",
        workspace_root="/repo/.cortex",
        mode="assist",
    )
    defaults.update(kwargs)
    return AutopilotSessionState(**defaults)


class TestBudgetPolicy:
    def test_within_budget(self) -> None:
        p = BudgetPolicy()
        state = _make_state(budget={"chars_injected": 500, "items_retrieved": 2})
        d = p.evaluate(state)
        assert d.allowed is True
        assert d.action == "proceed"

    def test_chars_exceeded_autopilot(self) -> None:
        p = BudgetPolicy()
        state = _make_state(mode="autopilot", budget={"chars_injected": 3000})
        d = p.evaluate(state)
        assert d.allowed is False
        assert d.action == "block"

    def test_chars_exceeded_assist(self) -> None:
        p = BudgetPolicy()
        state = _make_state(mode="assist", budget={"chars_injected": 3000})
        d = p.evaluate(state)
        assert d.allowed is False
        assert d.action == "warn"


class TestDocumentationRequiredPolicy:
    def test_no_changes(self) -> None:
        p = DocumentationRequiredPolicy()
        state = _make_state(changed_files=[])
        d = p.evaluate(state)
        assert d.allowed is True

    def test_changes_no_note_during_work(self) -> None:
        p = DocumentationRequiredPolicy()
        state = _make_state(mode="autopilot", changed_files=["a.py"], status="implementation_seen")
        d = p.evaluate(state)
        # Policy only enforces at finish time
        assert d.allowed is True

    def test_changes_no_note_at_finish_autopilot(self) -> None:
        p = DocumentationRequiredPolicy()
        state = _make_state(mode="autopilot", changed_files=["a.py"], status="finished")
        d = p.evaluate(state)
        assert d.allowed is False
        assert d.action == "block"

    def test_changes_with_note_at_finish(self) -> None:
        p = DocumentationRequiredPolicy()
        state = _make_state(changed_files=["a.py"], session_note_path="vault/sessions/x.md", status="finished")
        d = p.evaluate(state)
        assert d.allowed is True


class TestSpecRequiredPolicy:
    def test_deep_without_spec(self) -> None:
        p = SpecRequiredPolicy()
        state = _make_state(complexity="deep")
        d = p.evaluate(state)
        assert d.allowed is False
        assert d.action == "warn"

    def test_deep_with_spec(self) -> None:
        p = SpecRequiredPolicy()
        state = _make_state(complexity="deep", spec_path="vault/specs/x.md")
        d = p.evaluate(state)
        assert d.allowed is True


class TestHumanApprovalPolicy:
    def test_security_warns(self) -> None:
        p = HumanApprovalPolicy()
        state = _make_state(detected_task_type="security")
        d = p.evaluate(state)
        assert d.action == "warn"

    def test_deep_warns(self) -> None:
        p = HumanApprovalPolicy()
        state = _make_state(complexity="deep")
        d = p.evaluate(state)
        assert d.action == "warn"

    def test_fast_ok(self) -> None:
        p = HumanApprovalPolicy()
        state = _make_state(complexity="fast")
        d = p.evaluate(state)
        assert d.action == "proceed"


class TestAutoCheckpointPolicy:
    def test_no_changes(self) -> None:
        p = AutoCheckpointPolicy()
        state = _make_state(changed_files=[])
        d = p.evaluate(state)
        assert d.action == "proceed"

    def test_few_files_ok(self) -> None:
        p = AutoCheckpointPolicy()
        state = _make_state(changed_files=["a.py"])
        d = p.evaluate(state)
        assert d.action == "proceed"

    def test_many_files_no_checkpoint_autopilot(self) -> None:
        p = AutoCheckpointPolicy()
        state = _make_state(mode="autopilot", changed_files=[f"f{i}.py" for i in range(7)])
        d = p.evaluate(state)
        assert d.allowed is False
        assert d.action == "block"

    def test_many_files_no_checkpoint_assist(self) -> None:
        p = AutoCheckpointPolicy()
        state = _make_state(mode="assist", changed_files=[f"f{i}.py" for i in range(7)])
        d = p.evaluate(state)
        assert d.allowed is False
        assert d.action == "warn"

    def test_with_checkpoint_under_threshold(self) -> None:
        p = AutoCheckpointPolicy()
        ck = AutopilotCheckpoint(
            timestamp=datetime.now(),
            summary="ck",
            files_at_checkpoint=["f0.py", "f1.py", "f2.py", "f3.py", "f4.py", "f5.py"],
        )
        state = _make_state(
            changed_files=[f"f{i}.py" for i in range(7)],
            checkpoints=[ck],
        )
        d = p.evaluate(state)
        assert d.action == "proceed"

    def test_time_warning(self) -> None:
        p = AutoCheckpointPolicy()
        old = datetime.now() - timedelta(minutes=15)
        state = _make_state(
            created_at=old,
            changed_files=["a.py"],
        )
        d = p.evaluate(state)
        assert d.action == "warn"


class TestEvaluatePolicies:
    def test_empty(self) -> None:
        decisions = evaluate_policies([], _make_state())
        assert decisions == []

    def test_most_restrictive(self) -> None:
        decisions = [
            PolicyDecision(allowed=True, reason="ok", action="proceed"),
            PolicyDecision(allowed=False, reason="bad", action="block"),
            PolicyDecision(allowed=True, reason="meh", action="warn"),
        ]
        worst = most_restrictive(decisions)
        assert worst is not None
        assert worst.action == "block"

    def test_most_restrictive_empty(self) -> None:
        assert most_restrictive([]) is None

