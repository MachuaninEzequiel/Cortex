"""cortex.autopilot.state_store — Persistent state for Autopilot sessions."""
from __future__ import annotations

from pathlib import Path

from .models import AutopilotSessionState, AutopilotEvent
from .errors import SessionNotFoundError


class StateStore:
    """JSON/JSONL persistence for Autopilot state.

    Directory layout (resolved via *workspace_root*):
        run/autopilot/sessions/<session-id>.json
        run/autopilot/events/<session-id>.jsonl
    """

    def __init__(self, workspace_root: Path) -> None:
        self.root = workspace_root / "run" / "autopilot"
        self.sessions_dir = self.root / "sessions"
        self.events_dir = self.root / "events"

    def _ensure_dirs(self) -> None:
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.events_dir.mkdir(parents=True, exist_ok=True)

    def create_session(
        self,
        *,
        project_root: str,
        workspace_root: str,
        mode: str = "assist",
        user_request: str | None = None,
        title_hint: str | None = None,
    ) -> AutopilotSessionState:
        """Create a new session, persist it, and return it."""
        state = AutopilotSessionState(
            project_root=project_root,
            workspace_root=workspace_root,
            mode=mode,  # type: ignore[arg-type]
            user_request=user_request,
            title_hint=title_hint,
        )
        self.save_state(state)
        return state

    def save_state(self, state: AutopilotSessionState) -> Path:
        self._ensure_dirs()
        path = self.sessions_dir / f"{state.session_id}.json"
        path.write_text(
            state.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return path

    def load_state(self, session_id: str) -> AutopilotSessionState | None:
        path = self.sessions_dir / f"{session_id}.json"
        if not path.exists():
            return None
        return AutopilotSessionState.model_validate_json(
            path.read_text(encoding="utf-8")
        )

    def require_state(self, session_id: str) -> AutopilotSessionState:
        """Load a session or raise ``SessionNotFoundError``."""
        state = self.load_state(session_id)
        if state is None:
            raise SessionNotFoundError(f"Session {session_id} not found")
        return state

    def append_event(self, event: AutopilotEvent) -> None:
        self._ensure_dirs()
        path = self.events_dir / f"{event.session_id}.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")

    def load_events(self, session_id: str) -> list[AutopilotEvent]:
        path = self.events_dir / f"{session_id}.jsonl"
        if not path.exists():
            return []
        events = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(AutopilotEvent.model_validate_json(line))
        return events

    def list_sessions(self) -> list[str]:
        if not self.sessions_dir.exists():
            return []
        return [
            p.stem for p in self.sessions_dir.glob("*.json")
        ]

    def cleanup(self, *, older_than_days: int = 30, max_size_mb: float = 5.0) -> dict[str, list[str]]:
        """Archive or remove old/large event JSONL files.

        Returns:
            Dict with lists of archived and removed files.
        """
        import time
        archived: list[str] = []
        removed: list[str] = []
        if not self.events_dir.exists():
            return {"archived": archived, "removed": removed}

        archive_dir = self.root / "events_archive"
        archive_dir.mkdir(parents=True, exist_ok=True)

        now = time.time()
        for path in self.events_dir.glob("*.jsonl"):
            size_mb = path.stat().st_size / (1024 * 1024)
            age_days = (now - path.stat().st_mtime) / 86400

            if age_days > older_than_days:
                dest = archive_dir / path.name
                path.rename(dest)
                archived.append(str(dest))
            elif size_mb > max_size_mb:
                dest = archive_dir / path.name
                path.rename(dest)
                archived.append(str(dest))

        return {"archived": archived, "removed": removed}
