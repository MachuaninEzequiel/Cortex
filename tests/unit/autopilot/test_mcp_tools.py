"""Phase-03 tests for ``cortex.autopilot.mcp_tools``.

Every tool delegates to :class:`AutopilotService`; here we verify that
the MCP-facing surface returns stable, human-readable strings and
classifies errors correctly.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from cortex.autopilot.errors import AutopilotError, NoActiveSessionError
from cortex.autopilot.mcp_tools import AutopilotMCPTools, _format_error
from cortex.autopilot.policies import AutopilotMode, AutopilotPolicy
from cortex.autopilot.service import AutopilotService
from cortex.session.errors import SessionNotFound
from cortex.session.service import SessionService
from cortex.session.storage import SessionStorage

# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / ".cortex" / "sessions").mkdir(parents=True)
    (root / "config.yaml").write_text("episodic: {}\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
    (root / "README.md").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "i"], cwd=root, check=True)
    return root


@pytest.fixture
def service(repo: Path) -> AutopilotService:
    storage = SessionStorage(repo / ".cortex" / "sessions")
    sessions = SessionService(storage, repo)
    return AutopilotService(
        session_service=sessions,
        policy=AutopilotPolicy(),
        repo_root=repo,
    )


@pytest.fixture
def tools(service: AutopilotService) -> AutopilotMCPTools:
    return AutopilotMCPTools(service)


def _open_session(service: AutopilotService, repo: Path, summary: str = "demo session") -> str:
    spec_dir = repo / "vault" / "specs"
    spec_dir.mkdir(parents=True, exist_ok=True)
    spec_path = spec_dir / "2026-05-16_demo.md"
    spec_path.write_text("# demo\n", encoding="utf-8")
    record = service.session_service.open(
        spec_id="2026-05-16_demo",
        spec_path=spec_path,
        spec_summary=summary,
    )
    return record.session_id


# ── start ────────────────────────────────────────────────────────────


class TestStartTool:
    def test_happy_path(self, tools, service, repo) -> None:
        _open_session(service, repo, summary="refactor parsing")
        out = tools.start({"mode": "assist"})
        assert "Session adopted" in out
        assert "2026-05-16_demo" in out
        assert "Mode: assist" in out

    def test_without_session_reports_error(self, tools) -> None:
        out = tools.start({"mode": "assist"})
        assert out.startswith("Error")
        assert "active session" in out.lower()

    def test_invalid_mode_reports_error(self, tools, service, repo) -> None:
        _open_session(service, repo)
        out = tools.start({"mode": "hyperdrive"})
        assert out.startswith("Error")
        assert "hyperdrive" in out

    def test_security_warning_surfaced(self, tools, service, repo) -> None:
        _open_session(service, repo, summary="rotate OAuth secret tokens")
        out = tools.start({"mode": "assist"})
        assert "Warnings:" in out
        assert "security" in out.lower()


# ── preflight ───────────────────────────────────────────────────────


class TestPreflightTool:
    def test_runs_without_session(self, tools) -> None:
        out = tools.preflight({"user_request": "please implement JWT refresh"})
        assert out.startswith("Preflight")
        assert "task_type" not in out  # human-readable, not JSON

    def test_includes_task_type_value(self, tools) -> None:
        out = tools.preflight({"user_request": "fix the broken login bug"})
        assert "(" in out and ")" in out  # confidence/complexity block

    def test_changed_files_list(self, tools) -> None:
        out = tools.preflight({"changed_files": ["src/foo.py", "src/bar.py"]})
        assert "Preflight" in out


# ── checkpoint ──────────────────────────────────────────────────────


class TestCheckpointTool:
    def test_happy_path(self, tools, service, repo) -> None:
        _open_session(service, repo)
        out = tools.checkpoint(
            {
                "source": "manual",
                "note": "smoke",
                "artifacts_touched": ["src/a.py"],
            }
        )
        assert "Checkpoint recorded" in out
        assert "Total checkpoints: 1" in out

    def test_without_session(self, tools) -> None:
        out = tools.checkpoint({"source": "manual", "note": "smoke"})
        assert out.startswith("Error")

    def test_invalid_source(self, tools, service, repo) -> None:
        _open_session(service, repo)
        out = tools.checkpoint({"source": "from-mars", "note": "x"})
        assert out.startswith("Error")
        assert "from-mars" in out

    def test_out_of_scope_warning_surfaced(self, tools, service, repo) -> None:
        _open_session(service, repo)
        out = tools.checkpoint(
            {
                "source": "manual",
                "artifacts_touched": ["src/a.py", "src/b.py"],
                "files_in_scope": ["src/a.py"],
            }
        )
        assert "Warnings:" in out
        assert "outside spec scope" in out


# ── finish ──────────────────────────────────────────────────────────


class TestFinishTool:
    def test_manual_close(self, tools, service, repo) -> None:
        _open_session(service, repo)
        out = tools.finish({"auto": False})
        assert "Finish:" in out
        assert "Documented: False" in out

    def test_without_session(self, tools) -> None:
        out = tools.finish({"auto": False})
        assert out.startswith("Error")

    def test_already_closed_is_noop(self, tools, service, repo) -> None:
        _open_session(service, repo)
        tools.finish({"auto": False})
        out = tools.finish({"session_id": "2026-05-16_demo", "auto": False})
        assert "Finish" in out  # not blocked, just a no-op summary

    def test_blocked_by_policy_reports_block(
        self, repo: Path, service: AutopilotService
    ) -> None:
        # Build an autopilot-mode service that demands verified claims.
        _open_session(service, repo)
        autopilot_svc = AutopilotService(
            session_service=service.session_service,
            policy=AutopilotPolicy(
                mode=AutopilotMode.AUTOPILOT, pre_commit_verification=True
            ),
            repo_root=repo,
        )
        out = AutopilotMCPTools(autopilot_svc).finish({"auto": False})
        assert "blocked by policy" in out.lower()


# ── status ──────────────────────────────────────────────────────────


class TestStatusTool:
    def test_no_active(self, tools) -> None:
        out = tools.status({})
        assert "No active Autopilot session" in out

    def test_active(self, tools, service, repo) -> None:
        _open_session(service, repo)
        out = tools.status({})
        assert "Session: 2026-05-16_demo" in out
        assert "Mode: assist" in out
        assert "Inferred mode: byo" in out  # no checkpoints

    def test_unknown_id_returns_no_active(self, tools) -> None:
        out = tools.status({"session_id": "nonexistent"})
        assert "No active Autopilot session" in out


# ── _format_error ───────────────────────────────────────────────────


class TestFormatError:
    def test_autopilot_error(self) -> None:
        msg = _format_error("test_tool", AutopilotError("boom"))
        assert msg.startswith("Error (test_tool):")
        assert "boom" in msg

    def test_no_active_session_error_branch(self) -> None:
        msg = _format_error("test_tool", NoActiveSessionError("no session here"))
        assert msg.startswith("Error (test_tool):")
        assert "no session here" in msg

    def test_session_not_found_error(self) -> None:
        msg = _format_error("test_tool", SessionNotFound("x"))
        assert msg.startswith("Error (test_tool):")
        assert "Session not found" in msg

    def test_generic_exception_falls_through(self) -> None:
        msg = _format_error("test_tool", RuntimeError("kaboom"))
        assert "RuntimeError" in msg
        assert "kaboom" in msg
