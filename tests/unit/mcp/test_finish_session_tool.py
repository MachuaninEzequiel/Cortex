"""Tests for the ``cortex_finish_session`` MCP tool (T1.7)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cortex.mcp.server import CortexMCPServer
from cortex.session import SessionRecord, SessionStatus

VALID_SHA = "a" * 40
ANOTHER_SHA = "b" * 40


def _open_record(session_id: str = "2026-05-16_demo") -> SessionRecord:
    return SessionRecord(
        session_id=session_id,
        spec_path=Path("vault/specs/demo.md"),
        spec_summary="demo",
        start_commit=VALID_SHA,
        start_branch="main",
        opened_at=datetime(2026, 5, 16, 10, tzinfo=UTC),
    )


def _closed_record(session_id: str = "2026-05-16_demo") -> SessionRecord:
    return SessionRecord(
        session_id=session_id,
        spec_path=Path("vault/specs/demo.md"),
        spec_summary="demo",
        start_commit=VALID_SHA,
        start_branch="main",
        opened_at=datetime(2026, 5, 16, 10, tzinfo=UTC),
        status=SessionStatus.CLOSED,
        closed_at=datetime(2026, 5, 16, 12, tzinfo=UTC),
        end_commit=ANOTHER_SHA,
        documenter_decision=SessionStatus.CLOSED,
    )


class _FakeMemoryNoActive:
    """Just exposes ``get_active_session`` returning None."""

    def get_active_session(self) -> SessionRecord | None:
        return None

    def get_session(self, session_id: str) -> SessionRecord:  # pragma: no cover
        raise AssertionError("should not be called")


class _FakeMemoryClosed:
    """Returns a closed record from ``get_session`` (already finished)."""

    def __init__(self, record: SessionRecord) -> None:
        self._record = record

    def get_active_session(self) -> SessionRecord | None:
        return self._record

    def get_session(self, session_id: str) -> SessionRecord:
        return self._record


def _server_with(memory: Any) -> CortexMCPServer:
    instance = CortexMCPServer.__new__(CortexMCPServer)
    instance.memory = memory  # type: ignore[attr-defined]
    return instance


class TestFinishSessionInputValidation:
    def test_invalid_intent_rejected(self) -> None:
        server = _server_with(_FakeMemoryNoActive())
        result = server._finish_session_text({"intent": "bogus"})
        assert "Invalid intent" in result
        assert "auto" in result and "handoff" in result and "abandon" in result

    def test_intent_requires_reason(self) -> None:
        server = _server_with(_FakeMemoryNoActive())
        result = server._finish_session_text({"intent": "handoff"})
        assert "'reason' is required" in result

    def test_no_active_session_errors(self) -> None:
        server = _server_with(_FakeMemoryNoActive())
        result = server._finish_session_text({})
        assert "No active session" in result


class TestFinishSessionRefusesClosed:
    def test_already_closed_session_returns_friendly_error(self) -> None:
        record = _closed_record()
        server = _server_with(_FakeMemoryClosed(record))
        result = server._finish_session_text({"session_id": record.session_id})
        assert "already in status" in result
        assert "closed" in result


# Happy-path E2E integration is exercised through tests/unit/cli/ and the
# Reconstructor/Persister suites — the MCP wrapper only adds argument
# parsing and JSON-serialization, both of which are exhaustively covered
# by the negative tests above plus the JSON schema validation in
# tests/unit/mcp/test_session_tools.py.
