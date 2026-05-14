"""Tests for cortex.autopilot.mcp_tools."""
from __future__ import annotations

from pathlib import Path

import pytest

from cortex.autopilot.lifecycle import StartRequest
from cortex.autopilot.mcp_tools import AutopilotMCPTools, _format_error, _safe_call
from cortex.autopilot.service import AutopilotService
from cortex.autopilot.session_writer import VaultSessionWriter
from cortex.autopilot.state_store import StateStore


@pytest.fixture
def mcp_tools(tmp_path: Path) -> AutopilotMCPTools:
    """Fixture mirrors production wiring: state store + vault session writer."""
    store = StateStore(tmp_path)
    writer = VaultSessionWriter(tmp_path / "vault")
    svc = AutopilotService(state_store=store, session_writer=writer)
    return AutopilotMCPTools(svc)


class TestStart:
    def test_start(self, mcp_tools: AutopilotMCPTools) -> None:
        repo = Path("/tmp/repo")
        result = mcp_tools.start({
            "project_root": str(repo),
            "workspace_root": str(repo / ".cortex"),
            "mode": "autopilot",
            "user_request": "Fix login",
        })
        assert "Session started" in result
        assert "autopilot" in result

    def test_start_missing_project_root(self, mcp_tools: AutopilotMCPTools) -> None:
        result = mcp_tools.start({"workspace_root": "/repo/.cortex"})
        assert "Error" in result
        assert "Missing required argument" in result


class TestPreflight:
    def test_preflight(self, mcp_tools: AutopilotMCPTools, tmp_path: Path) -> None:
        start_res = mcp_tools._svc.start(
            StartRequest(project_root=str(tmp_path), workspace_root=str(tmp_path))
        )
        sid = start_res.session_id
        result = mcp_tools.preflight({
            "session_id": sid,
            "user_request": "Fix the login bug in auth.py",
            "changed_files": ["auth.py"],
        })
        assert "Preflight" in result
        assert any(t in result for t in ("fast-code", "security", "ambiguous", "noop"))

    def test_preflight_missing_session(self, mcp_tools: AutopilotMCPTools) -> None:
        result = mcp_tools.preflight({"session_id": "nosuch"})
        assert "Error" in result
        assert "Session not found" in result


class TestCheckpoint:
    def test_checkpoint(self, mcp_tools: AutopilotMCPTools, tmp_path: Path) -> None:
        start_res = mcp_tools._svc.start(
            StartRequest(project_root=str(tmp_path), workspace_root=str(tmp_path))
        )
        sid = start_res.session_id
        result = mcp_tools.checkpoint({
            "session_id": sid,
            "summary": "Fixed auth",
            "files_at_checkpoint": ["auth.py"],
            "verified": True,
        })
        assert "Checkpoint recorded" in result
        assert "Total checkpoints: 1" in result

    def test_checkpoint_missing_session(self, mcp_tools: AutopilotMCPTools) -> None:
        result = mcp_tools.checkpoint({"session_id": "bad", "summary": "x"})
        assert "Error" in result


class TestFinish:
    def test_finish_auto(self, mcp_tools: AutopilotMCPTools, tmp_path: Path) -> None:
        start_res = mcp_tools._svc.start(
            StartRequest(project_root=str(tmp_path), workspace_root=str(tmp_path))
        )
        sid = start_res.session_id
        result = mcp_tools.finish({"session_id": sid, "auto": True})
        assert "Finish" in result
        assert "Saved: True" in result
        assert "Draft" in result

    def test_finish_no_auto(self, mcp_tools: AutopilotMCPTools, tmp_path: Path) -> None:
        start_res = mcp_tools._svc.start(
            StartRequest(project_root=str(tmp_path), workspace_root=str(tmp_path))
        )
        sid = start_res.session_id
        result = mcp_tools.finish({"session_id": sid, "auto": False})
        assert "Saved: False" in result

    def test_finish_missing_session(self, mcp_tools: AutopilotMCPTools) -> None:
        result = mcp_tools.finish({"session_id": "bad"})
        assert "Error" in result


class TestStatus:
    def test_status_no_session(self, mcp_tools: AutopilotMCPTools) -> None:
        result = mcp_tools.status({})
        assert "No active" in result

    def test_status_with_session(self, mcp_tools: AutopilotMCPTools, tmp_path: Path) -> None:
        start_res = mcp_tools._svc.start(
            StartRequest(project_root=str(tmp_path), workspace_root=str(tmp_path))
        )
        sid = start_res.session_id
        result = mcp_tools.status({"session_id": sid})
        assert f"Session: {sid}" in result


class TestHelpers:
    def test_format_error_session_not_found(self) -> None:
        from cortex.autopilot.errors import SessionNotFoundError
        result = _format_error("preflight", SessionNotFoundError("abc"))
        assert "Session not found" in result

    def test_safe_call_success(self) -> None:
        result = _safe_call("test", lambda x: "ok", {})
        assert result == "ok"

    def test_safe_call_failure(self) -> None:
        def _boom(_: dict) -> str:
            raise ValueError("boom")
        result = _safe_call("test", _boom, {})
        assert "Error" in result
        assert "boom" in result
