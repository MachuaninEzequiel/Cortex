"""cortex.autopilot.cli — Headless CLI for the Autopilot module.

This is the only connection between the historic CLI and Autopilot.
All business logic delegates to ``AutopilotService``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

from cortex.workspace.layout import WorkspaceLayout
from cortex.autopilot.errors import AutopilotError, SessionNotFoundError
from cortex.autopilot.lifecycle import (
    CheckpointRequest,
    FinishRequest,
    PreflightRequest,
    StartRequest,
)
from cortex.autopilot.service import AutopilotService
from cortex.autopilot.state_store import StateStore

app = typer.Typer(
    name="autopilot",
    help="Cortex Autopilot — autonomous workflow layer.",
    add_completion=False,
)


def _resolve_service(project_root: str | None) -> AutopilotService:
    """Discover workspace layout and build an ``AutopilotService``."""
    root = Path(project_root).expanduser().resolve() if project_root else Path.cwd().resolve()
    return AutopilotService.from_project_root(root)


def _output(data: dict[str, object], json_mode: bool) -> None:
    if json_mode:
        typer.echo(json.dumps(data, indent=2, default=str))
    else:
        for key, value in data.items():
            typer.echo(f"{key}: {value}")


# ---------------------------------------------------------------------------
# start
# ---------------------------------------------------------------------------
@app.command()
def start(
    project_root: str | None = typer.Option(
        None, "--project-root", help="Absolute path to the project root."
    ),
    mode: str = typer.Option("assist", "--mode", help="Mode: observe, assist, autopilot."),
    request: str | None = typer.Option(None, "--request", help="User request text."),
    title_hint: str | None = typer.Option(None, "--title-hint", help="Short title hint."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Start a new Autopilot session."""
    svc = _resolve_service(project_root)
    root = svc._store.root.parent.parent  # workspace_root -> repo_root (best effort)
    # Better: resolve from layout
    layout = WorkspaceLayout.discover(Path(project_root) if project_root else Path.cwd())

    result = svc.start(
        StartRequest(
            project_root=str(layout.repo_root),
            workspace_root=str(layout.workspace_root),
            mode=mode,
            user_request=request,
            title_hint=title_hint,
        )
    )

    payload = {
        "session_id": result.session_id,
        "status": result.state.status,
        "mode": result.state.mode,
    }
    _output(payload, json_output)


# ---------------------------------------------------------------------------
# preflight
# ---------------------------------------------------------------------------
@app.command()
def preflight(
    session_id: str = typer.Option(..., "--session-id", help="Session ID."),
    request: str | None = typer.Option(None, "--request", help="User request text."),
    changed_files: list[str] = typer.Option([], "--file", help="Changed file (repeatable)."),
    project_root: str | None = typer.Option(
        None, "--project-root", help="Absolute path to the project root."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Run preflight detection for a session."""
    svc = _resolve_service(project_root)
    try:
        result = svc.preflight(
            PreflightRequest(
                session_id=session_id,
                user_request=request,
                changed_files=changed_files,
            )
        )
    except SessionNotFoundError as exc:
        if json_output:
            typer.echo(json.dumps({"error": str(exc)}), err=True)
        else:
            typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc

    payload = {
        "session_id": session_id,
        "task_type": result.detection.task_type,
        "confidence": result.detection.confidence,
        "can_proceed": result.can_proceed,
        "policy_decisions": [
            {"allowed": d.allowed, "action": d.action, "reason": d.reason}
            for d in result.policy_decisions
        ],
    }
    _output(payload, json_output)


# ---------------------------------------------------------------------------
# checkpoint
# ---------------------------------------------------------------------------
@app.command()
def checkpoint(
    session_id: str = typer.Option(..., "--session-id", help="Session ID."),
    summary: str = typer.Option(..., "--summary", help="Checkpoint summary."),
    files: list[str] = typer.Option([], "--file", help="Files at this checkpoint (repeatable)."),
    verified: bool = typer.Option(False, "--verified", help="Whether the checkpoint is verified."),
    project_root: str | None = typer.Option(
        None, "--project-root", help="Absolute path to the project root."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Record a checkpoint for a session."""
    svc = _resolve_service(project_root)
    try:
        result = svc.checkpoint(
            CheckpointRequest(
                session_id=session_id,
                summary=summary,
                files_at_checkpoint=files,
                verified=verified,
            )
        )
    except SessionNotFoundError as exc:
        if json_output:
            typer.echo(json.dumps({"error": str(exc)}), err=True)
        else:
            typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc

    payload = {
        "session_id": session_id,
        "status": result.state.status,
        "checkpoints_count": len(result.state.checkpoints),
    }
    _output(payload, json_output)


# ---------------------------------------------------------------------------
# finish
# ---------------------------------------------------------------------------
@app.command()
def finish(
    session_id: str = typer.Option(..., "--session-id", help="Session ID."),
    auto: bool = typer.Option(False, "--auto", help="Auto-generate draft if missing data."),
    project_root: str | None = typer.Option(
        None, "--project-root", help="Absolute path to the project root."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Finish a session and optionally persist a session note."""
    svc = _resolve_service(project_root)
    try:
        result = svc.finish(FinishRequest(session_id=session_id, auto=auto))
    except SessionNotFoundError as exc:
        if json_output:
            typer.echo(json.dumps({"error": str(exc)}), err=True)
        else:
            typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc

    payload: dict[str, object] = {
        "session_id": session_id,
        "status": result.state.status,
        "saved": result.saved,
    }
    if result.draft:
        payload["draft_title"] = result.draft.title
        payload["draft_confidence"] = result.draft.confidence
        payload["draft_warnings"] = result.draft.warnings
    else:
        payload["reason"] = "No draft generated"

    _output(payload, json_output)


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------
@app.command()
def status(
    session_id: str | None = typer.Option(None, "--session-id", help="Session ID (optional)."),
    project_root: str | None = typer.Option(
        None, "--project-root", help="Absolute path to the project root."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Show the current Autopilot status."""
    svc = _resolve_service(project_root)
    result = svc.status(session_id)

    if not result.active:
        payload: dict[str, object] = {"active": False, "message": "No active session found"}
        _output(payload, json_output)
        return

    assert result.state is not None
    payload = {
        "active": True,
        "session_id": result.state.session_id,
        "status": result.state.status,
        "mode": result.state.mode,
        "detected_task_type": result.state.detected_task_type,
        "complexity": result.state.complexity,
        "event_count": result.event_count,
        "warnings": result.state.warnings,
    }
    _output(payload, json_output)


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------
@app.command()
def doctor(
    project_root: str | None = typer.Option(
        None, "--project-root", help="Absolute path to the project root."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Diagnose the Autopilot installation and state. (Read-only)"""
    from cortex.autopilot.doctor import run_diagnosis

    root = Path(project_root).expanduser().resolve() if project_root else Path.cwd().resolve()
    report = run_diagnosis(root)

    checks = [
        {
            "name": c.name,
            "ok": c.ok,
            "detail": c.detail,
            "action": c.action,
        }
        for c in report.checks
    ]
    payload: dict[str, object] = {
        "project_root": str(root),
        "ok": report.ok,
        "checks": checks,
        "warnings": report.warnings,
    }
    _output(payload, json_output)


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
@app.command()
def report(
    project_root: str | None = typer.Option(
        None, "--project-root", help="Absolute path to the project root."
    ),
    last: int = typer.Option(10, "--last", help="Number of recent sessions to report."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Generate a report of recent Autopilot sessions."""
    from cortex.autopilot.reporting import generate_report

    root = Path(project_root).expanduser().resolve() if project_root else Path.cwd().resolve()
    sessions = generate_report(root, last_n=last)

    payload: dict[str, object] = {
        "project_root": str(root),
        "sessions": [
            {
                "session_id": s.session_id,
                "status": s.status,
                "mode": s.mode,
                "task_type": s.task_type,
                "complexity": s.complexity,
                "checkpoints": s.checkpoints,
                "events": s.events,
                "chars_injected": s.chars_injected,
                "items_retrieved": s.items_retrieved,
                "warnings": s.warnings,
            }
            for s in sessions
        ],
    }
    _output(payload, json_output)


# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------
@app.command()
def cleanup(
    project_root: str | None = typer.Option(
        None, "--project-root", help="Absolute path to the project root."
    ),
    older_than: int = typer.Option(30, "--older-than", help="Archive event JSONL files older than N days."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Archive old Autopilot event JSONL files."""
    root = Path(project_root).expanduser().resolve() if project_root else Path.cwd().resolve()
    layout = WorkspaceLayout.discover(root)
    store = StateStore(layout.workspace_root)
    result = store.cleanup(older_than_days=older_than)
    payload: dict[str, object] = {
        "project_root": str(root),
        "archived": result["archived"],
        "removed": result["removed"],
    }
    _output(payload, json_output)
