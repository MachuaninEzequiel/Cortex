"""Tests for the shrunk ``cortex.autopilot.models`` surface (Phase 03)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from cortex.autopilot.models import (
    DetectionRequest,
    DetectionResult,
    PolicyDecision,
)


class TestDetectionRequest:
    def test_defaults(self) -> None:
        req = DetectionRequest()
        assert req.user_request is None
        assert req.changed_files == []
        assert req.git_diff_stat is None
        assert req.session_state is None

    def test_explicit_values(self) -> None:
        req = DetectionRequest(
            user_request="fix bug",
            changed_files=["a.py"],
            git_diff_stat="a.py | 1",
        )
        assert req.user_request == "fix bug"
        assert req.changed_files == ["a.py"]
        assert req.git_diff_stat == "a.py | 1"

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            DetectionRequest(unknown_field=1)  # type: ignore[call-arg]


class TestDetectionResult:
    def test_minimal(self) -> None:
        r = DetectionResult(task_type="noop")
        assert r.task_type == "noop"
        assert r.confidence == 0.0
        assert r.reason == ""
        assert r.suggested_complexity == "none"

    def test_rejects_unknown_task_type(self) -> None:
        with pytest.raises(ValidationError):
            DetectionResult(task_type="cooking")  # type: ignore[arg-type]

    def test_rejects_unknown_complexity(self) -> None:
        with pytest.raises(ValidationError):
            DetectionResult(task_type="noop", suggested_complexity="extreme")  # type: ignore[arg-type]


class TestPolicyDecision:
    def test_defaults(self) -> None:
        d = PolicyDecision(allowed=True, reason="ok")
        assert d.allowed is True
        assert d.action == "proceed"
        assert d.degrade_to is None

    def test_rejects_unknown_action(self) -> None:
        with pytest.raises(ValidationError):
            PolicyDecision(allowed=False, reason="x", action="explode")  # type: ignore[arg-type]


# HookSessionStartOutput removed in Phase 04 cleanup — see models.py docstring.
