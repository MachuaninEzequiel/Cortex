"""Tests for the MCP ``cortex_session_*`` tools (Phase 00 / T0.7)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from cortex.mcp.server import CortexMCPServer
from cortex.session import (
    Checkpoint,
    CheckpointSource,
    SessionMode,
    SessionRecord,
    SessionStatus,
)

# Constants shared by helpers.
VALID_SHA = "a" * 40
ANOTHER_SHA = "b" * 40


# ---------------------------------------------------------------------------
# Fake AgentMemory — just enough surface for the 5 tools.
# ---------------------------------------------------------------------------


def _make_record(
    *,
    session_id: str = "2026-05-16_demo",
    status: SessionStatus = SessionStatus.OPEN,
    checkpoints: list[Checkpoint] | None = None,
    mode: SessionMode = SessionMode.UNKNOWN,
    closed_at: datetime | None = None,
    end_commit: str | None = None,
    documenter_decision: SessionStatus | None = None,
) -> SessionRecord:
    return SessionRecord(
        session_id=session_id,
        spec_path=Path("vault/specs/demo.md"),
        spec_summary="demo",
        start_commit=VALID_SHA,
        start_branch="main",
        opened_at=datetime(2026, 5, 16, 10, tzinfo=UTC),
        status=status,
        mode=mode,
        checkpoints=checkpoints or [],
        closed_at=closed_at,
        end_commit=end_commit,
        documenter_decision=documenter_decision,
    )


class _FakeMemory:
    """Captures calls and returns canned :class:`SessionRecord` instances."""

    def __init__(self, *, active: SessionRecord | None = None) -> None:
        self.opened: dict[str, object] | None = None
        self.checkpointed: dict[str, object] | None = None
        self.closed: dict[str, object] | None = None
        self._active = active
        self._records: dict[str, SessionRecord] = {}
        self._list_filter: str | None = None
        if active is not None:
            self._records[active.session_id] = active

    # open
    def open_session(
        self, *, spec_id: str, spec_path: str | Path, spec_summary: str
    ) -> SessionRecord:
        record = _make_record(session_id=spec_id)
        self.opened = {"spec_id": spec_id, "spec_path": spec_path, "spec_summary": spec_summary}
        self._records[record.session_id] = record
        self._active = record
        return record

    # checkpoint
    def checkpoint_session(self, session_id: str, **kwargs: object) -> SessionRecord:
        self.checkpointed = {"session_id": session_id, **kwargs}
        cp = Checkpoint(
            timestamp=datetime(2026, 5, 16, 11, tzinfo=UTC),
            source=CheckpointSource(kwargs["source"]),
            note=str(kwargs.get("note", "")),
        )
        record = _make_record(session_id=session_id, checkpoints=[cp])
        self._records[session_id] = record
        return record

    # close
    def close_session(self, session_id: str, **kwargs: object) -> SessionRecord:
        self.closed = {"session_id": session_id, **kwargs}
        record = _make_record(
            session_id=session_id,
            status=SessionStatus(str(kwargs["status"])),
            mode=SessionMode.BYO,
            closed_at=datetime(2026, 5, 16, 12, tzinfo=UTC),
            end_commit=ANOTHER_SHA,
            documenter_decision=SessionStatus(str(kwargs["documenter_decision"])),
        )
        self._records[session_id] = record
        return record

    # read
    def get_session(self, session_id: str) -> SessionRecord:
        return self._records[session_id]

    def get_active_session(self) -> SessionRecord | None:
        return self._active

    def list_sessions(self, status: str | None = None) -> list[SessionRecord]:
        self._list_filter = status
        records = list(self._records.values())
        if status:
            records = [r for r in records if r.status.value == status]
        return records


@pytest.fixture
def server() -> CortexMCPServer:
    instance = CortexMCPServer.__new__(CortexMCPServer)
    instance.memory = _FakeMemory()  # type: ignore[attr-defined]
    return instance


# ---------------------------------------------------------------------------
# cortex_session_open
# ---------------------------------------------------------------------------


class TestSessionOpenTool:
    def test_happy_path_returns_json(self, server: CortexMCPServer) -> None:
        result = server._session_open_text(
            {"spec_id": "2026-05-16_demo", "spec_path": "vault/specs/demo.md"}
        )
        data = json.loads(result)
        assert data["session_id"] == "2026-05-16_demo"
        assert data["start_commit"] == VALID_SHA
        assert data["start_branch"] == "main"

    def test_missing_required_fields_returns_error(self, server: CortexMCPServer) -> None:
        assert "required" in server._session_open_text({})
        assert "required" in server._session_open_text({"spec_id": "x"})


# ---------------------------------------------------------------------------
# cortex_session_checkpoint
# ---------------------------------------------------------------------------


class TestSessionCheckpointTool:
    def test_happy_path(self, server: CortexMCPServer) -> None:
        result = server._session_checkpoint_text(
            {
                "session_id": "2026-05-16_demo",
                "source": "cortex-SDDwork",
                "verified_claims": ["wrote auth.py"],
                "note": "fast track",
            }
        )
        data = json.loads(result)
        assert data["session_id"] == "2026-05-16_demo"
        assert data["checkpoint_count"] == 1
        assert data["last_checkpoint_at"] is not None

    def test_invalid_source_rejected_with_helpful_list(self, server: CortexMCPServer) -> None:
        result = server._session_checkpoint_text(
            {"session_id": "2026-05-16_demo", "source": "made-up"}
        )
        assert "Invalid source" in result
        assert "cortex-SDDwork" in result  # lists allowed values

    def test_missing_fields_error(self, server: CortexMCPServer) -> None:
        assert "required" in server._session_checkpoint_text({})


# ---------------------------------------------------------------------------
# cortex_session_close
# ---------------------------------------------------------------------------


class TestSessionCloseTool:
    def test_happy_path(self, server: CortexMCPServer) -> None:
        result = server._session_close_text(
            {
                "session_id": "2026-05-16_demo",
                "status": "closed",
                "documenter_decision": "closed",
                "session_note_path": "vault/sessions/demo.md",
                "adrs_created": [],
            }
        )
        data = json.loads(result)
        assert data["session_id"] == "2026-05-16_demo"
        assert data["end_commit"] == ANOTHER_SHA
        assert data["mode_inferred"] == "byo"
        assert data["closed_at"] is not None

    def test_invalid_status_rejected(self, server: CortexMCPServer) -> None:
        result = server._session_close_text(
            {
                "session_id": "2026-05-16_demo",
                "status": "running",
                "documenter_decision": "closed",
            }
        )
        assert "Invalid status" in result

    def test_invalid_documenter_decision_rejected(self, server: CortexMCPServer) -> None:
        result = server._session_close_text(
            {
                "session_id": "2026-05-16_demo",
                "status": "closed",
                "documenter_decision": "garbage",
            }
        )
        assert "Invalid documenter_decision" in result

    def test_missing_fields_error(self, server: CortexMCPServer) -> None:
        assert "required" in server._session_close_text({})


# ---------------------------------------------------------------------------
# cortex_session_status
# ---------------------------------------------------------------------------


class TestSessionStatusTool:
    def test_explicit_id_returns_full_record(self) -> None:
        record = _make_record()
        server = CortexMCPServer.__new__(CortexMCPServer)
        server.memory = _FakeMemory(active=record)  # type: ignore[attr-defined]
        result = server._session_status_text({"session_id": "2026-05-16_demo"})
        data = json.loads(result)
        assert data["session_id"] == "2026-05-16_demo"
        assert data["status"] == "open"
        assert data["start_commit"] == VALID_SHA

    def test_no_id_uses_active_session(self) -> None:
        record = _make_record(session_id="2026-05-16_active")
        server = CortexMCPServer.__new__(CortexMCPServer)
        server.memory = _FakeMemory(active=record)  # type: ignore[attr-defined]
        result = server._session_status_text({})
        data = json.loads(result)
        assert data["session_id"] == "2026-05-16_active"

    def test_no_active_session_returns_error(self) -> None:
        server = CortexMCPServer.__new__(CortexMCPServer)
        server.memory = _FakeMemory()  # type: ignore[attr-defined]
        assert "No active session" in server._session_status_text({})


# ---------------------------------------------------------------------------
# cortex_session_list
# ---------------------------------------------------------------------------


class TestSessionListTool:
    def test_returns_summarized_list(self) -> None:
        record = _make_record()
        server = CortexMCPServer.__new__(CortexMCPServer)
        server.memory = _FakeMemory(active=record)  # type: ignore[attr-defined]
        result = server._session_list_text({})
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["session_id"] == "2026-05-16_demo"
        # Should NOT include heavy fields like the full checkpoints array.
        assert "checkpoints" not in data[0]
        assert data[0]["checkpoint_count"] == 0

    def test_status_filter_forwarded(self) -> None:
        record = _make_record()
        server = CortexMCPServer.__new__(CortexMCPServer)
        memory = _FakeMemory(active=record)
        server.memory = memory  # type: ignore[attr-defined]
        server._session_list_text({"status": "open"})
        assert memory._list_filter == "open"

    def test_empty_list_returns_empty_array(self) -> None:
        server = CortexMCPServer.__new__(CortexMCPServer)
        server.memory = _FakeMemory()  # type: ignore[attr-defined]
        assert server._session_list_text({}) == "[]"
