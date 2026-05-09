"""Tests for cortex.autopilot.delegation — two-stage review engine."""
from __future__ import annotations

import pytest

from cortex.autopilot.delegation import (
    DelegationEngine,
    ReviewVerdict,
    _StageResult,
    get_task_result,
    list_tasks,
    register_task,
)
from cortex.autopilot.models import AutopilotSessionState, DelegationResult


class TestStageResults:
    def test_stage_result_passed(self) -> None:
        sr = _StageResult(passed=True, reason="OK")
        assert sr.passed is True
        assert sr.reason == "OK"

    def test_stage_result_failed(self) -> None:
        sr = _StageResult(passed=False, reason="bad")
        assert sr.passed is False


class TestStage1SpecCompliance:
    def test_fails_on_failed_status(self) -> None:
        state = AutopilotSessionState(session_id="s1", project_root="/r", workspace_root="/r/.cortex")
        result = DelegationResult(task_id="t1", status="failed")
        engine = DelegationEngine()
        verdict = engine.review(result, state)
        assert not verdict.accepted
        assert not verdict.stage_1_passed
        assert "failed" in verdict.reason.lower()

    def test_fails_on_empty_diff_with_files(self) -> None:
        state = AutopilotSessionState(session_id="s1", project_root="/r", workspace_root="/r/.cortex")
        result = DelegationResult(
            task_id="t1", status="completed", files_changed=["a.py"], diff_summary=""
        )
        engine = DelegationEngine()
        verdict = engine.review(result, state)
        assert not verdict.accepted
        assert "diff_summary" in verdict.reason.lower() or "empty" in verdict.reason.lower()

    def test_fails_on_out_of_scope_files(self) -> None:
        state = AutopilotSessionState(
            session_id="s1",
            project_root="/r",
            workspace_root="/r/.cortex",
            changed_files=["a.py"],
        )
        result = DelegationResult(
            task_id="t1", status="completed", files_changed=["b.py"], diff_summary="changed b"
        )
        engine = DelegationEngine()
        verdict = engine.review(result, state)
        assert not verdict.accepted
        assert "scope" in verdict.reason.lower() or "outside" in verdict.reason.lower()

    def test_passes_when_compliant(self) -> None:
        state = AutopilotSessionState(
            session_id="s1",
            project_root="/r",
            workspace_root="/r/.cortex",
            changed_files=["a.py"],
        )
        result = DelegationResult(
            task_id="t1",
            status="completed",
            files_changed=["a.py"],
            diff_summary="changed a",
            tests_passed=True,
        )
        engine = DelegationEngine()
        verdict = engine.review(result, state)
        assert verdict.accepted
        assert verdict.stage_1_passed
        assert verdict.stage_2_passed


class TestStage2Quality:
    def test_fails_on_rejection_reason(self) -> None:
        state = AutopilotSessionState(session_id="s1", project_root="/r", workspace_root="/r/.cortex")
        result = DelegationResult(
            task_id="t1",
            status="completed",
            files_changed=["a.py"],
            diff_summary="changed a",
            rejection_reason="Quality issues",
        )
        engine = DelegationEngine()
        verdict = engine.review(result, state)
        assert not verdict.accepted
        assert verdict.stage_1_passed is True
        assert verdict.stage_2_passed is False
        assert "rejection" in verdict.reason.lower()

    def test_fails_on_tests_not_passed(self) -> None:
        state = AutopilotSessionState(session_id="s1", project_root="/r", workspace_root="/r/.cortex")
        result = DelegationResult(
            task_id="t1",
            status="completed",
            files_changed=["a.py"],
            diff_summary="changed a",
            tests_passed=False,
        )
        engine = DelegationEngine()
        verdict = engine.review(result, state)
        assert not verdict.accepted
        assert verdict.stage_2_passed is False
        assert "tests" in verdict.reason.lower()

    def test_passes_with_none_tests(self) -> None:
        state = AutopilotSessionState(session_id="s1", project_root="/r", workspace_root="/r/.cortex")
        result = DelegationResult(
            task_id="t1",
            status="completed",
            files_changed=["a.py"],
            diff_summary="changed a",
            tests_passed=None,
        )
        engine = DelegationEngine()
        verdict = engine.review(result, state)
        assert verdict.accepted


class TestTaskRegistry:
    def test_register_and_get(self) -> None:
        result = DelegationResult(task_id="t1", status="completed")
        register_task(result)
        assert get_task_result("t1") == result
        assert get_task_result("missing") is None

    def test_list_tasks(self) -> None:
        register_task(DelegationResult(task_id="t2", status="completed"))
        assert "t2" in list_tasks()


class TestServiceReviewDelegation:
    def test_accepted_creates_checkpoint(self, tmp_path) -> None:
        from cortex.autopilot.lifecycle import StartRequest
        from cortex.autopilot.service import AutopilotService

        svc = AutopilotService.from_project_root(tmp_path)
        start_res = svc.start(
            StartRequest(project_root=str(tmp_path), workspace_root=str(tmp_path))
        )
        result = DelegationResult(
            task_id="t1",
            status="completed",
            files_changed=["a.py"],
            diff_summary="changed a",
            tests_passed=True,
        )
        verdict = svc.review_delegation(start_res.session_id, result)
        assert verdict.accepted

        status = svc.status(start_res.session_id)
        assert status.state is not None
        assert len(status.state.checkpoints) == 1
        assert status.state.checkpoints[0].summary == "Delegation accepted: t1"

    def test_rejected_logs_event(self, tmp_path) -> None:
        from cortex.autopilot.lifecycle import StartRequest
        from cortex.autopilot.service import AutopilotService

        svc = AutopilotService.from_project_root(tmp_path)
        start_res = svc.start(
            StartRequest(project_root=str(tmp_path), workspace_root=str(tmp_path))
        )
        result = DelegationResult(
            task_id="t1",
            status="failed",
            files_changed=[],
            diff_summary="",
        )
        verdict = svc.review_delegation(start_res.session_id, result)
        assert not verdict.accepted

        status = svc.status(start_res.session_id)
        assert status.state is not None
        assert any("t1 rejected" in w for w in status.state.warnings)
