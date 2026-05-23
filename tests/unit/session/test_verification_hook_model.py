"""Tests for the :class:`VerificationHook` Pydantic model (Phase 01 / T1.1)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from cortex.session import VerificationHook


class TestVerificationHookModel:
    def test_defaults(self) -> None:
        hook = VerificationHook(name="tests", command="pytest")
        assert hook.required is True
        assert hook.success_criteria == "exit code 0"
        assert hook.timeout_seconds == 300

    def test_name_must_not_be_empty(self) -> None:
        with pytest.raises(ValidationError):
            VerificationHook(name="", command="pytest")

    def test_command_must_not_be_empty(self) -> None:
        with pytest.raises(ValidationError):
            VerificationHook(name="tests", command="")

    def test_timeout_range(self) -> None:
        with pytest.raises(ValidationError):
            VerificationHook(name="tests", command="pytest", timeout_seconds=0)
        with pytest.raises(ValidationError):
            VerificationHook(name="tests", command="pytest", timeout_seconds=2000)
        # Boundaries OK.
        VerificationHook(name="tests", command="pytest", timeout_seconds=1)
        VerificationHook(name="tests", command="pytest", timeout_seconds=1800)

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="Extra inputs"):
            VerificationHook(  # type: ignore[call-arg]
                name="tests", command="pytest", bogus="nope"
            )

    def test_frozen(self) -> None:
        hook = VerificationHook(name="tests", command="pytest")
        with pytest.raises(ValidationError):
            hook.required = False  # type: ignore[misc]

    def test_roundtrip_via_dict(self) -> None:
        hook = VerificationHook(
            name="tests",
            command="pytest tests/auth/",
            required=False,
            timeout_seconds=60,
        )
        data = hook.model_dump(mode="json")
        assert VerificationHook.model_validate(data) == hook
