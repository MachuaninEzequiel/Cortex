"""Tests for cortex.autopilot.service."""
from __future__ import annotations

from pathlib import Path

import pytest

from cortex.autopilot.lifecycle import (
    CheckpointRequest,
    FinishRequest,
    PreflightRequest,
    StartRequest,
)
from cortex.autopilot.models import AutopilotEvent
from cortex.autopilot.service import AutopilotService
from cortex.autopilot.session_writer import VaultSessionWriter
from cortex.autopilot.state_store import StateStore


@pytest.fixture
def service(tmp_path: Path) -> AutopilotService:
    """Default service wired with a real VaultSessionWriter under tmp_path.

    Tests that need to assert ``finish --auto`` actually persists a file
    can read from ``tmp_path / "vault" / "sessions"``.
    """
    store = StateStore(tmp_path)
    writer = VaultSessionWriter(tmp_path / "vault")
    return AutopilotService(state_store=store, session_writer=writer)


@pytest.fixture
def service_without_writer(tmp_path: Path) -> AutopilotService:
    """Service with no writer to exercise the degraded contract."""
    store = StateStore(tmp_path)
    return AutopilotService(state_store=store)


class TestStart:
    def test_creates_session(self, service: AutopilotService) -> None:
        req = StartRequest(project_root="/repo", workspace_root="/repo/.cortex")
        res = service.start(req)
        assert res.session_id
        assert res.state.status == "started"
        assert res.state.mode == "assist"

    def test_persists_event(self, service: AutopilotService) -> None:
        req = StartRequest(project_root="/repo", workspace_root="/repo/.cortex", mode="autopilot")
        res = service.start(req)
        events = service._store.load_events(res.session_id)
        assert len(events) == 1
        assert events[0].event_type == "start"

    def test_no_onnx_load(self, service: AutopilotService) -> None:
        # start() must not trigger any heavy initialization
        req = StartRequest(project_root="/repo", workspace_root="/repo/.cortex")
        res = service.start(req)
        assert res.state.session_id


class TestPreflight:
    def test_detects_fast_code(self, service: AutopilotService) -> None:
        start = service.start(StartRequest(project_root="/repo", workspace_root="/repo/.cortex"))
        pre = service.preflight(
            PreflightRequest(
                session_id=start.session_id,
                user_request="Implement user profile page with email validation",
                changed_files=["profiles.py"],
            )
        )
        assert pre.detection.task_type == "fast-code"
        assert pre.state.detected_task_type == "fast-code"
        assert pre.state.status == "preflight_done"
        assert pre.can_proceed is True

    def test_detects_ambiguous(self, service: AutopilotService) -> None:
        start = service.start(StartRequest(project_root="/repo", workspace_root="/repo/.cortex"))
        pre = service.preflight(
            PreflightRequest(
                session_id=start.session_id,
                user_request="fix login",
            )
        )
        assert pre.detection.task_type == "ambiguous"
        assert pre.can_proceed is True  # ambiguous doesn't block via policy by default

    def test_no_user_request(self, service: AutopilotService) -> None:
        start = service.start(StartRequest(project_root="/repo", workspace_root="/repo/.cortex"))
        pre = service.preflight(PreflightRequest(session_id=start.session_id))
        assert pre.detection.task_type == "ambiguous"  # no request -> ambiguous
        assert pre.state.warnings == []

    def test_leaves_event(self, service: AutopilotService) -> None:
        start = service.start(StartRequest(project_root="/repo", workspace_root="/repo/.cortex"))
        service.preflight(
            PreflightRequest(session_id=start.session_id, user_request="What is the auth flow?")
        )
        events = service._store.load_events(start.session_id)
        assert any(e.event_type == "preflight" for e in events)


class TestCheckpoint:
    def test_adds_checkpoint(self, service: AutopilotService) -> None:
        start = service.start(StartRequest(project_root="/repo", workspace_root="/repo/.cortex"))
        ck = service.checkpoint(
            CheckpointRequest(
                session_id=start.session_id,
                summary="Implemented login fix",
                files_at_checkpoint=["login.py"],
                verified=True,
            )
        )
        assert len(ck.state.checkpoints) == 1
        assert ck.state.status == "implementation_seen"

    def test_leaves_event(self, service: AutopilotService) -> None:
        start = service.start(StartRequest(project_root="/repo", workspace_root="/repo/.cortex"))
        service.checkpoint(
            CheckpointRequest(session_id=start.session_id, summary="ck", files_at_checkpoint=[])
        )
        events = service._store.load_events(start.session_id)
        assert any(e.event_type == "checkpoint" for e in events)


class TestFinish:
    def test_auto_finish_persists_to_disk(
        self, service: AutopilotService, tmp_path: Path
    ) -> None:
        """``finish --auto`` must create the session note file on disk.

        Regression: previously ``saved=True`` was returned without any
        write_text() call, leaving ``session_note_path`` pointing at a
        non-existent file.
        """
        start = service.start(StartRequest(project_root="/repo", workspace_root="/repo/.cortex"))
        service.checkpoint(
            CheckpointRequest(
                session_id=start.session_id,
                summary="Done",
                files_at_checkpoint=["a.py"],
            )
        )
        fin = service.finish(FinishRequest(session_id=start.session_id, auto=True))
        assert fin.saved is True
        assert fin.draft is not None
        assert fin.state.status == "documented"

        # The contract: documented ⇒ file on disk.
        assert fin.state.session_note_path is not None
        note_path = Path(fin.state.session_note_path)
        assert note_path.exists(), f"Session note not written: {note_path}"
        assert note_path.parent == tmp_path / "vault" / "sessions"
        content = note_path.read_text(encoding="utf-8")
        assert "session_id:" in content
        assert "tags:" in content
        assert "autopilot" in content

    def test_finish_auto_no_writer_does_not_claim_documented(
        self, service_without_writer: AutopilotService
    ) -> None:
        """Without a writer, the service must NOT mark the session documented.

        This preserves the invariant: status=='documented' implies the
        session note exists on disk.
        """
        svc = service_without_writer
        start = svc.start(StartRequest(project_root="/repo", workspace_root="/repo/.cortex"))
        svc.checkpoint(
            CheckpointRequest(
                session_id=start.session_id,
                summary="Done",
                files_at_checkpoint=["a.py"],
            )
        )
        fin = svc.finish(FinishRequest(session_id=start.session_id, auto=True))
        assert fin.draft is not None
        assert fin.saved is False
        assert fin.state.status == "finished"
        assert any("session_writer" in w for w in fin.state.warnings)

    def test_finish_blocked_by_policy(self, service: AutopilotService) -> None:
        # In autopilot mode with changes but no checkpoint, auto-checkpoint policy blocks
        start = service.start(
            StartRequest(project_root="/repo", workspace_root="/repo/.cortex", mode="autopilot")
        )
        # Simulate many file changes without checkpoint
        state = service._store.load_state(start.session_id)
        state.changed_files = [f"f{i}.py" for i in range(10)]
        service._store.save_state(state)

        fin = service.finish(FinishRequest(session_id=start.session_id, auto=True))
        assert fin.state.status == "finished"
        assert fin.draft is not None
        assert fin.draft.confidence == "auto-draft"
        assert fin.saved is False

    def test_finish_without_auto(self, service: AutopilotService) -> None:
        start = service.start(StartRequest(project_root="/repo", workspace_root="/repo/.cortex"))
        fin = service.finish(FinishRequest(session_id=start.session_id, auto=False))
        assert fin.saved is False
        assert fin.state.status == "finished"

    def test_event_records_session_note_path(
        self, service: AutopilotService
    ) -> None:
        """The finish event must include the persisted path for telemetry."""
        start = service.start(StartRequest(project_root="/repo", workspace_root="/repo/.cortex"))
        service.checkpoint(
            CheckpointRequest(
                session_id=start.session_id,
                summary="Done",
                files_at_checkpoint=["a.py"],
            )
        )
        service.finish(FinishRequest(session_id=start.session_id, auto=True))
        events = service._store.load_events(start.session_id)
        finish_events = [e for e in events if e.event_type == "finish"]
        assert finish_events, "no finish event recorded"
        assert finish_events[-1].payload["saved"] is True
        assert finish_events[-1].payload["session_note_path"] is not None


class TestStatus:
    def test_no_sessions(self, service: AutopilotService) -> None:
        st = service.status()
        assert st.active is False

    def test_with_session(self, service: AutopilotService) -> None:
        start = service.start(StartRequest(project_root="/repo", workspace_root="/repo/.cortex"))
        st = service.status(start.session_id)
        assert st.active is True
        assert st.state is not None
        assert st.state.session_id == start.session_id

    def test_latest_session(self, service: AutopilotService) -> None:
        s1 = service.start(StartRequest(project_root="/repo", workspace_root="/repo/.cortex"))
        s2 = service.start(StartRequest(project_root="/repo", workspace_root="/repo/.cortex"))
        st = service.status()
        assert st.active is True
        assert st.state is not None
        assert st.state.session_id == s2.session_id
