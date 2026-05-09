"""Tests for cortex.autopilot.models."""
from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from cortex.autopilot.models import (
    AutopilotBudgetSnapshot,
    AutopilotCheckpoint,
    AutopilotSessionState,
    AutopilotEvent,
    DetectionRequest,
    DetectionResult,
    PolicyDecision,
    SessionDraft,
    HookSessionStartOutput,
    DelegationResult,
)


class TestAutopilotBudgetSnapshot:
    def test_defaults(self) -> None:
        b = AutopilotBudgetSnapshot()
        assert b.chars_injected == 0
        assert b.items_retrieved == 0
        assert b.embeddings_used is False
        assert b.subagents_spawned == 0
        assert b.deep_track_reason is None

    def test_roundtrip(self) -> None:
        b = AutopilotBudgetSnapshot(
            chars_injected=1200,
            items_retrieved=3,
            embeddings_used=True,
            deep_track_reason="refactor",
        )
        json_data = b.model_dump_json()
        restored = AutopilotBudgetSnapshot.model_validate_json(json_data)
        assert restored.chars_injected == 1200
        assert restored.deep_track_reason == "refactor"


class TestAutopilotCheckpoint:
    def test_roundtrip(self) -> None:
        now = datetime(2026, 5, 9, 12, 0, 0)
        ck = AutopilotCheckpoint(
            timestamp=now,
            summary="Initial checkpoint",
            files_at_checkpoint=["a.py"],
            verified=True,
        )
        restored = AutopilotCheckpoint.model_validate_json(ck.model_dump_json())
        assert restored.summary == "Initial checkpoint"
        assert restored.verified is True


class TestAutopilotSessionState:
    def test_defaults(self) -> None:
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
        )
        assert state.schema_version == 1
        assert len(state.session_id) == 12
        assert state.status == "started"
        assert state.mode == "assist"
        assert state.complexity == "none"
        assert state.budget.chars_injected == 0
        assert state.changed_files == []

    def test_serialization_deserialization(self) -> None:
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            mode="autopilot",
            user_request="Fix login bug",
            detected_task_type="fast-code",
            complexity="fast",
        )
        json_data = state.model_dump_json()
        restored = AutopilotSessionState.model_validate_json(json_data)
        assert restored.session_id == state.session_id
        assert restored.mode == "autopilot"
        assert restored.user_request == "Fix login bug"
        assert restored.complexity == "fast"
        assert restored.budget.chars_injected == 0

    def test_session_id_is_stable(self) -> None:
        """Session ID must not change on re-serialization."""
        state = AutopilotSessionState(
            project_root="/repo",
            workspace_root="/repo/.cortex",
        )
        sid = state.session_id
        restored = AutopilotSessionState.model_validate_json(state.model_dump_json())
        assert restored.session_id == sid

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AutopilotSessionState(
                project_root="/repo",
                workspace_root="/repo/.cortex",
                status="invalid",  # type: ignore[call-arg]
            )

    def test_invalid_mode_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AutopilotSessionState(
                project_root="/repo",
                workspace_root="/repo/.cortex",
                mode="invalid",  # type: ignore[call-arg]
            )


class TestAutopilotEvent:
    def test_roundtrip(self) -> None:
        ev = AutopilotEvent(
            session_id="abc123",
            event_type="start",
            source="cli",
            payload={"foo": "bar"},
        )
        restored = AutopilotEvent.model_validate_json(ev.model_dump_json())
        assert restored.event_type == "start"
        assert restored.source == "cli"
        assert restored.payload == {"foo": "bar"}


class TestDetectionRequest:
    def test_defaults(self) -> None:
        req = DetectionRequest()
        assert req.user_request is None
        assert req.changed_files == []


class TestDetectionResult:
    def test_defaults(self) -> None:
        res = DetectionResult(task_type="noop")
        assert res.task_type == "noop"
        assert res.confidence == 0.0
        assert res.suggested_complexity == "none"

    def test_roundtrip(self) -> None:
        res = DetectionResult(
            task_type="fast-code",
            confidence=0.85,
            reason="Small change",
            suggested_complexity="fast",
        )
        restored = DetectionResult.model_validate_json(res.model_dump_json())
        assert restored.task_type == "fast-code"
        assert restored.confidence == 0.85


class TestPolicyDecision:
    def test_roundtrip(self) -> None:
        d = PolicyDecision(
            allowed=False,
            reason="budget exceeded",
            action="degrade",
            degrade_to="assist",
        )
        restored = PolicyDecision.model_validate_json(d.model_dump_json())
        assert restored.allowed is False
        assert restored.degrade_to == "assist"


class TestSessionDraft:
    def test_roundtrip(self) -> None:
        draft = SessionDraft(
            title="Fix login",
            body="# Summary\nChanged auth.py",
            confidence="auto-draft",
            warnings=["No tests run"],
            source_events=3,
        )
        restored = SessionDraft.model_validate_json(draft.model_dump_json())
        assert restored.confidence == "auto-draft"
        assert restored.source_events == 3


class TestHookSessionStartOutput:
    def test_roundtrip(self) -> None:
        out = HookSessionStartOutput(
            session_id="abc123",
            mode="assist",
            bootstrap_content="use cortex",
            budget_profile="fast_code",
            available_tools=["cortex_context"],
            cortex_version="2.0.0",
        )
        restored = HookSessionStartOutput.model_validate_json(out.model_dump_json())
        assert restored.mode == "assist"
        assert restored.available_tools == ["cortex_context"]


class TestDelegationResult:
    def test_roundtrip(self) -> None:
        dr = DelegationResult(
            task_id="t1",
            status="rejected",
            rejection_reason="spec mismatch",
        )
        restored = DelegationResult.model_validate_json(dr.model_dump_json())
        assert restored.status == "rejected"
        assert restored.rejection_reason == "spec mismatch"
