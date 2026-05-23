"""Tests for :mod:`cortex.session.errors`.

Only verifies the type hierarchy — the exceptions carry no logic.
"""

from __future__ import annotations

import pytest

from cortex.session.errors import (
    InvalidStateTransition,
    NoActiveSession,
    SessionAlreadyExists,
    SessionError,
    SessionNotFound,
    SessionStorageCorrupted,
)


@pytest.mark.parametrize(
    "exc_cls",
    [
        SessionNotFound,
        SessionAlreadyExists,
        InvalidStateTransition,
        SessionStorageCorrupted,
        NoActiveSession,
    ],
)
def test_each_specific_error_is_a_session_error(exc_cls: type[SessionError]) -> None:
    instance = exc_cls("test message")
    assert isinstance(instance, SessionError)
    assert str(instance) == "test message"


def test_session_error_is_an_exception() -> None:
    assert issubclass(SessionError, Exception)


def test_can_catch_specific_via_base() -> None:
    with pytest.raises(SessionError):
        raise SessionNotFound("2026-05-16_x")
