"""Tests for cortex.autopilot.state_store."""
from __future__ import annotations

from pathlib import Path

import pytest

from cortex.autopilot.state_store import StateStore
from cortex.autopilot.models import AutopilotSessionState, AutopilotEvent
from cortex.autopilot.errors import SessionNotFoundError


class TestStateStoreNewLayout:
    """Tests using a new-layout workspace (workspace_root == repo_root / '.cortex')."""

    @pytest.fixture
    def store(self, tmp_path: Path) -> StateStore:
        workspace = tmp_path / ".cortex"
        workspace.mkdir()
        (workspace / "workspace.yaml").write_text("layout_version: 2\n")
        return StateStore(workspace)

    def test_create_session_generates_stable_id(self, store: StateStore) -> None:
        state = store.create_session(
            project_root="/repo",
            workspace_root="/repo/.cortex",
        )
        assert len(state.session_id) == 12
        assert state.status == "started"
        assert state.mode == "assist"

    def test_save_and_load_roundtrip(self, store: StateStore) -> None:
        state = store.create_session(
            project_root="/repo",
            workspace_root="/repo/.cortex",
            mode="autopilot",
            user_request="Fix bug",
        )
        loaded = store.load_state(state.session_id)
        assert loaded is not None
        assert loaded.session_id == state.session_id
        assert loaded.mode == "autopilot"
        assert loaded.user_request == "Fix bug"

    def test_load_missing_returns_none(self, store: StateStore) -> None:
        assert store.load_state("nonexistent") is None

    def test_require_state_raises_on_missing(self, store: StateStore) -> None:
        with pytest.raises(SessionNotFoundError):
            store.require_state("nonexistent")

    def test_append_event(self, store: StateStore) -> None:
        state = store.create_session(
            project_root="/repo",
            workspace_root="/repo/.cortex",
        )
        event = AutopilotEvent(
            session_id=state.session_id,
            event_type="preflight",
            source="cli",
            payload={"request": "Fix bug"},
        )
        store.append_event(event)

        events = store.load_events(state.session_id)
        assert len(events) == 1
        assert events[0].event_type == "preflight"
        assert events[0].payload["request"] == "Fix bug"

    def test_append_multiple_events(self, store: StateStore) -> None:
        state = store.create_session(
            project_root="/repo",
            workspace_root="/repo/.cortex",
        )
        for i in range(3):
            store.append_event(
                AutopilotEvent(
                    session_id=state.session_id,
                    event_type="checkpoint",
                    source="agent",
                    payload={"index": i},
                )
            )
        events = store.load_events(state.session_id)
        assert len(events) == 3
        assert events[2].payload["index"] == 2

    def test_load_events_empty(self, store: StateStore) -> None:
        assert store.load_events("no-such-session") == []

    def test_list_sessions(self, store: StateStore) -> None:
        s1 = store.create_session(project_root="/repo", workspace_root="/repo/.cortex")
        s2 = store.create_session(project_root="/repo", workspace_root="/repo/.cortex")
        sessions = store.list_sessions()
        assert sorted(sessions) == sorted([s1.session_id, s2.session_id])

    def test_list_sessions_empty_dir(self, tmp_path: Path) -> None:
        store = StateStore(tmp_path / ".cortex")
        assert store.list_sessions() == []

    def test_persists_under_run_autopilot(self, store: StateStore) -> None:
        state = store.create_session(project_root="/repo", workspace_root="/repo/.cortex")
        expected = store.root / "sessions" / f"{state.session_id}.json"
        assert expected.exists()


class TestStateStoreLegacyLayout:
    """Tests using a legacy workspace (workspace_root == repo_root)."""

    @pytest.fixture
    def store(self, tmp_path: Path) -> StateStore:
        # In legacy layout workspace_root == repo_root (no .cortex subdir as root)
        (tmp_path / "config.yaml").write_text("test: true\n")
        return StateStore(tmp_path)

    def test_create_session_legacy(self, store: StateStore) -> None:
        state = store.create_session(
            project_root="/repo",
            workspace_root="/repo",
        )
        assert state.session_id
        # Should live under repo_root/run/autopilot because workspace_root == repo_root
        expected = store.root / "sessions" / f"{state.session_id}.json"
        assert expected.exists()

    def test_save_and_load_legacy(self, store: StateStore) -> None:
        state = store.create_session(
            project_root="/repo",
            workspace_root="/repo",
        )
        loaded = store.load_state(state.session_id)
        assert loaded is not None
        assert loaded.project_root == "/repo"
