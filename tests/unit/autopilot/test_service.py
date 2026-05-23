"""Tests for the Phase-03 :class:`AutopilotService`.

Exercises the new policy + enforcer + session-service wiring against a
real :class:`SessionService` on a temporary git repo. The documenter
path (``finish(auto=True)``) is verified separately under
``tests/unit/documenter/`` and the E2E suite — here we only check that
``finish(auto=False)`` closes the record and that the policy enforces
its blocks.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from cortex.autopilot.errors import AutopilotError, NoActiveSessionError
from cortex.autopilot.lifecycle import (
    AutopilotCheckpointRequest,
    AutopilotFinishRequest,
    AutopilotPreflightRequest,
    AutopilotStartRequest,
)
from cortex.autopilot.policies import AutopilotMode, AutopilotPolicy
from cortex.autopilot.service import AutopilotService
from cortex.session.models import SessionStatus
from cortex.session.service import SessionService
from cortex.session.storage import SessionStorage

# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Tiny git repo with one commit on ``main``."""
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
    (root / "README.md").write_text("# repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "initial"], cwd=root, check=True
    )
    return root


@pytest.fixture
def sessions_dir(tmp_path: Path) -> Path:
    d = tmp_path / "sessions"
    d.mkdir()
    return d


@pytest.fixture
def session_service(sessions_dir: Path, repo: Path) -> SessionService:
    return SessionService(SessionStorage(sessions_dir), repo)


@pytest.fixture
def make_service(session_service: SessionService, repo: Path):
    def _build(policy: AutopilotPolicy | None = None) -> AutopilotService:
        return AutopilotService(
            session_service=session_service,
            policy=policy or AutopilotPolicy(),
            repo_root=repo,
        )

    return _build


def _open_spec_session(svc: SessionService, repo: Path) -> str:
    spec_dir = repo / "vault" / "specs"
    spec_dir.mkdir(parents=True, exist_ok=True)
    spec_path = spec_dir / "2026-05-16_demo.md"
    spec_path.write_text("# demo\n", encoding="utf-8")
    record = svc.open(
        spec_id="2026-05-16_demo",
        spec_path=spec_path,
        spec_summary="demo spec for tests",
    )
    return record.session_id


# ── start ────────────────────────────────────────────────────────────


class TestStart:
    def test_requires_active_session(self, make_service) -> None:
        svc = make_service()
        with pytest.raises(NoActiveSessionError):
            svc.start(AutopilotStartRequest())

    def test_returns_active_session_and_policy(
        self, make_service, session_service, repo: Path
    ) -> None:
        _open_spec_session(session_service, repo)
        svc = make_service()
        result = svc.start(AutopilotStartRequest())
        assert result.session.status is SessionStatus.OPEN
        assert result.policy.mode is AutopilotMode.ASSIST

    def test_mode_override_is_respected(
        self, make_service, session_service, repo: Path
    ) -> None:
        _open_spec_session(session_service, repo)
        svc = make_service(AutopilotPolicy(mode=AutopilotMode.OBSERVE))
        result = svc.start(AutopilotStartRequest(mode=AutopilotMode.AUTOPILOT))
        assert result.policy.mode is AutopilotMode.AUTOPILOT
        assert result.policy.pre_commit_verification is True


# ── preflight ───────────────────────────────────────────────────────


class TestPreflight:
    def test_runs_without_active_session(self, make_service) -> None:
        svc = make_service()
        result = svc.preflight(
            AutopilotPreflightRequest(user_request="please refactor the parser")
        )
        assert result.detection.task_type in {
            "question-only", "docs-only", "fast-code", "deep-code",
            "security", "ambiguous", "noop",
        }


# ── checkpoint ──────────────────────────────────────────────────────


class TestCheckpoint:
    def test_requires_active_session(self, make_service) -> None:
        svc = make_service()
        with pytest.raises(NoActiveSessionError):
            svc.checkpoint(AutopilotCheckpointRequest(source="manual"))

    def test_appends_and_returns_warnings(
        self, make_service, session_service, repo: Path
    ) -> None:
        _open_spec_session(session_service, repo)
        svc = make_service()
        result = svc.checkpoint(
            AutopilotCheckpointRequest(
                source="manual",
                artifacts_touched=["src/a.py", "src/b.py"],
                files_in_scope=["src/a.py"],
            )
        )
        assert len(result.session.checkpoints) == 1
        assert result.checkpoint.artifacts_touched == ["src/a.py", "src/b.py"]
        assert any("outside spec scope" in w for w in result.warnings)

    def test_rejects_unknown_source(
        self, make_service, session_service, repo: Path
    ) -> None:
        _open_spec_session(session_service, repo)
        svc = make_service()
        with pytest.raises(AutopilotError):
            svc.checkpoint(AutopilotCheckpointRequest(source="from-mars"))


# ── finish ──────────────────────────────────────────────────────────


class TestFinishManual:
    def test_closes_without_documenting(
        self, make_service, session_service, repo: Path
    ) -> None:
        _open_spec_session(session_service, repo)
        svc = make_service()
        result = svc.finish(AutopilotFinishRequest(auto=False))
        assert result.session.status is SessionStatus.CLOSED
        assert result.documented is False

    def test_handoff_intent_translates_to_handoff_status(
        self, make_service, session_service, repo: Path
    ) -> None:
        _open_spec_session(session_service, repo)
        svc = make_service()
        result = svc.finish(AutopilotFinishRequest(auto=False, intent="handoff"))
        assert result.session.status is SessionStatus.HANDOFF

    def test_blocks_in_autopilot_without_verified(
        self, make_service, session_service, repo: Path
    ) -> None:
        _open_spec_session(session_service, repo)
        svc = make_service(
            AutopilotPolicy(mode=AutopilotMode.AUTOPILOT, pre_commit_verification=True)
        )
        result = svc.finish(AutopilotFinishRequest(auto=False))
        assert result.blocked is True
        assert "verified claims" in result.blocked_reason

    def test_already_closed_session_is_noop(
        self, make_service, session_service, repo: Path
    ) -> None:
        _open_spec_session(session_service, repo)
        svc = make_service()
        first = svc.finish(AutopilotFinishRequest(auto=False))
        assert first.session.status is SessionStatus.CLOSED
        # Calling finish again on the same id is idempotent.
        target_id = first.session.session_id
        second = svc.finish(AutopilotFinishRequest(session_id=target_id, auto=False))
        assert "no-op" in second.summary

    def test_auto_without_memory_factory_errors(
        self, make_service, session_service, repo: Path
    ) -> None:
        _open_spec_session(session_service, repo)
        svc = make_service()
        with pytest.raises(AutopilotError, match="memory_factory"):
            svc.finish(AutopilotFinishRequest(auto=True))


# ── status ──────────────────────────────────────────────────────────


class TestStatus:
    def test_no_active_session(self, make_service) -> None:
        svc = make_service()
        result = svc.status()
        assert result.active is False

    def test_active_session(
        self, make_service, session_service, repo: Path
    ) -> None:
        _open_spec_session(session_service, repo)
        svc = make_service()
        result = svc.status()
        assert result.active is True
        assert result.session is not None
        assert result.session.status is SessionStatus.OPEN
        assert result.inferred_mode == "byo"  # no checkpoints yet

    def test_lookup_by_unknown_id_returns_inactive(self, make_service) -> None:
        svc = make_service()
        result = svc.status("does-not-exist")
        assert result.active is False
