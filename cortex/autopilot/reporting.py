"""cortex.autopilot.reporting — Session reports and summaries."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cortex.autopilot.service import AutopilotService
from cortex.autopilot.state_store import StateStore
from cortex.workspace.layout import WorkspaceLayout


@dataclass
class SessionReport:
    session_id: str
    status: str
    mode: str
    task_type: str | None
    complexity: str
    checkpoints: int
    events: int
    chars_injected: int
    items_retrieved: int
    warnings: list[str] = field(default_factory=list)


def generate_report(
    project_root: Path | None = None,
    *,
    last_n: int = 10,
) -> list[SessionReport]:
    """Generate a report for the *last_n* most recent sessions."""
    root = project_root or Path.cwd()
    layout = WorkspaceLayout.discover(root)
    store = StateStore(layout.workspace_root)

    sessions = store.list_sessions()
    if not sessions:
        return []

    # Load states to sort by updated_at descending
    states = []
    for sid in sessions:
        state = store.load_state(sid)
        if state:
            states.append(state)

    states.sort(key=lambda s: s.updated_at, reverse=True)
    states = states[:last_n]

    reports: list[SessionReport] = []
    for state in states:
        events = store.load_events(state.session_id)
        reports.append(
            SessionReport(
                session_id=state.session_id,
                status=state.status,
                mode=state.mode,
                task_type=state.detected_task_type,
                complexity=state.complexity,
                checkpoints=len(state.checkpoints),
                events=len(events),
                chars_injected=state.budget.chars_injected,
                items_retrieved=state.budget.items_retrieved,
                warnings=list(state.warnings),
            )
        )
    return reports
