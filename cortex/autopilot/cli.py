"""cortex.autopilot.cli — Typer subapp for ``cortex autopilot ...`` commands.

Phase 03 refactor: every command delegates to the new
:class:`AutopilotService`, which itself is a thin layer over the canonical
:class:`cortex.session.service.SessionService`.

Commands kept (UX continuity for users who already know them):
    start         — adopt the active session under a chosen mode.
    preflight     — dry-run the detector pipeline (no state mutation).
    checkpoint    — append a checkpoint to the active session.
    finish        — close the active session; ``--auto`` runs the documenter.
    status        — describe the active or named session.
    doctor        — run the Autopilot diagnostic checks.
    install       — install an IDE hook (delegates to legacy adapters
                    until T3.6 ships the new ``cortex session hooks`` flow).
    uninstall     — inverse of ``install``.

Commands removed (Phase 03 §11.3 + §11.4):
    cleanup       — JSONL events no longer exist; sessions live in
                    ``.cortex/sessions/`` and are managed by
                    ``cortex session``.
    report        — fully covered by ``cortex session list``.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from cortex.autopilot.errors import AutopilotError, NoActiveSessionError
from cortex.autopilot.lifecycle import (
    AutopilotCheckpointRequest,
    AutopilotFinishRequest,
    AutopilotPreflightRequest,
    AutopilotStartRequest,
)
from cortex.autopilot.policies import AutopilotMode
from cortex.autopilot.service import AutopilotService
from cortex.session.errors import SessionNotFound

app = typer.Typer(
    name="autopilot",
    help="Cortex Autopilot — policy + hooks layer over Sessions.",
    add_completion=False,
)


# ── Helpers ──────────────────────────────────────────────────────────


def _resolve_root(project_root: str | None) -> Path:
    return Path(project_root).expanduser().resolve() if project_root else Path.cwd().resolve()


def _resolve_service(project_root: str | None) -> AutopilotService:
    return AutopilotService.from_project_root(_resolve_root(project_root))


def _emit(payload: dict[str, object], json_mode: bool) -> None:
    if json_mode:
        typer.echo(json.dumps(payload, indent=2, default=str))
        return
    for key, value in payload.items():
        typer.echo(f"{key}: {value}")


def _parse_mode(raw: str | None) -> AutopilotMode | None:
    if raw is None:
        return None
    try:
        return AutopilotMode(raw)
    except ValueError as exc:
        valid = ", ".join(m.value for m in AutopilotMode)
        typer.echo(f"Invalid --mode {raw!r}; valid: {valid}", err=True)
        raise typer.Exit(2) from exc


def _abort_no_session(exc: AutopilotError, json_mode: bool) -> None:
    msg = str(exc)
    if json_mode:
        typer.echo(json.dumps({"error": msg}), err=True)
    else:
        typer.echo(f"✗ {msg}", err=True)
    raise typer.Exit(1)


# ── start ────────────────────────────────────────────────────────────


@app.command()
def start(
    mode: str = typer.Option("assist", "--mode", help="Mode: observe, assist, autopilot."),
    project_root: str | None = typer.Option(
        None, "--project-root", help="Absolute path to the project root."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Adopt the active session under the requested mode and surface warnings."""
    parsed_mode = _parse_mode(mode)
    svc = _resolve_service(project_root)
    try:
        result = svc.start(AutopilotStartRequest(mode=parsed_mode))
    except NoActiveSessionError as exc:
        _abort_no_session(exc, json_output)
        return
    payload: dict[str, object] = {
        "session_id": result.session.session_id,
        "mode": result.policy.mode.value,
        "status": result.session.status.value,
        "warnings": result.warnings,
    }
    _emit(payload, json_output)


# ── preflight (dry-run de detectors) ─────────────────────────────────


@app.command()
def preflight(
    request: str | None = typer.Option(None, "--request", help="User request text."),
    changed_files: list[str] = typer.Option([], "--file", help="Changed file (repeatable)."),
    project_root: str | None = typer.Option(
        None, "--project-root", help="Absolute path to the project root."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Run the detector pipeline as a dry-run; do not touch any session state."""
    svc = _resolve_service(project_root)
    result = svc.preflight(
        AutopilotPreflightRequest(
            user_request=request,
            changed_files=changed_files,
        )
    )
    payload: dict[str, object] = {
        "task_type": result.detection.task_type,
        "confidence": result.detection.confidence,
        "reason": result.detection.reason,
        "suggested_complexity": result.detection.suggested_complexity,
    }
    _emit(payload, json_output)


# ── checkpoint ───────────────────────────────────────────────────────


@app.command()
def checkpoint(
    source: str = typer.Option(
        "manual", "--source", help="CheckpointSource value (e.g. manual, cortex-SDDwork)."
    ),
    note: str = typer.Option("", "--note", help="Free-form note for the next step."),
    verified_claim: list[str] = typer.Option(
        [], "--verified-claim", help="A verified claim (repeatable)."
    ),
    unverified_claim: list[str] = typer.Option(
        [], "--unverified-claim", help="A claim not yet verified (repeatable)."
    ),
    artifact: list[str] = typer.Option(
        [], "--artifact", help="Artifact path touched (repeatable)."
    ),
    files_in_scope: list[str] = typer.Option(
        [],
        "--in-scope",
        help="Spec scope path (repeatable); enables out-of-scope warning.",
    ),
    project_root: str | None = typer.Option(
        None, "--project-root", help="Absolute path to the project root."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Append a checkpoint to the active session."""
    svc = _resolve_service(project_root)
    try:
        result = svc.checkpoint(
            AutopilotCheckpointRequest(
                source=source,
                verified_claims=verified_claim,
                unverified_claims=unverified_claim,
                artifacts_touched=artifact,
                note=note,
                files_in_scope=files_in_scope or None,
            )
        )
    except NoActiveSessionError as exc:
        _abort_no_session(exc, json_output)
        return
    except AutopilotError as exc:
        _abort_no_session(exc, json_output)
        return
    payload: dict[str, object] = {
        "session_id": result.session.session_id,
        "checkpoints_count": len(result.session.checkpoints),
        "warnings": result.warnings,
    }
    _emit(payload, json_output)


# ── finish ──────────────────────────────────────────────────────────


@app.command()
def finish(
    auto: bool = typer.Option(
        False,
        "--auto",
        help="Invoke the documenter pipeline (reconstruct, verify, persist).",
    ),
    handoff: bool = typer.Option(False, "--handoff", help="Force the session to close as HANDOFF."),
    abandon: bool = typer.Option(
        False, "--abandon", help="Force the session to close as ABANDONED."
    ),
    reason: str = typer.Option("", "--reason", help="Reason recorded when --handoff or --abandon."),
    session_id: str | None = typer.Option(
        None, "--session-id", help="Explicit session id (default: active)."
    ),
    project_root: str | None = typer.Option(
        None, "--project-root", help="Absolute path to the project root."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Close the active session — ``--auto`` runs the canonical documenter."""
    if handoff and abandon:
        typer.echo("--handoff and --abandon are mutually exclusive.", err=True)
        raise typer.Exit(2)
    intent = "closed"
    if handoff:
        intent = "handoff"
    if abandon:
        intent = "abandoned"
    svc = _resolve_service(project_root)
    try:
        result = svc.finish(
            AutopilotFinishRequest(
                session_id=session_id,
                auto=auto,
                intent=intent,
                reason=reason,
            )
        )
    except NoActiveSessionError as exc:
        _abort_no_session(exc, json_output)
        return
    except AutopilotError as exc:
        _abort_no_session(exc, json_output)
        return
    if result.blocked:
        if json_output:
            typer.echo(
                json.dumps(
                    {
                        "blocked": True,
                        "reason": result.blocked_reason,
                        "warnings": result.warnings,
                    }
                ),
                err=True,
            )
        else:
            typer.echo(f"✗ blocked by policy: {result.blocked_reason}", err=True)
        raise typer.Exit(1)

    payload: dict[str, object] = {
        "session_id": result.session.session_id,
        "status": result.session.status.value,
        "documented": result.documented,
        "summary": result.summary,
        "warnings": result.warnings,
    }
    if result.session_note_path:
        payload["session_note_path"] = result.session_note_path
    if result.adrs_created:
        payload["adrs_created"] = result.adrs_created
    _emit(payload, json_output)


# ── status ───────────────────────────────────────────────────────────


@app.command()
def status(
    session_id: str | None = typer.Option(None, "--session-id", help="Session ID (optional)."),
    project_root: str | None = typer.Option(
        None, "--project-root", help="Absolute path to the project root."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Show the active or named session."""
    svc = _resolve_service(project_root)
    try:
        result = svc.status(session_id)
    except SessionNotFound as exc:
        if json_output:
            typer.echo(json.dumps({"error": str(exc)}), err=True)
        else:
            typer.echo(f"✗ {exc}", err=True)
        raise typer.Exit(1) from exc

    if not result.active or result.session is None:
        payload: dict[str, object] = {
            "active": False,
            "policy_mode": result.policy.mode.value if result.policy else None,
        }
        _emit(payload, json_output)
        return

    session = result.session
    payload = {
        "active": True,
        "session_id": session.session_id,
        "status": session.status.value,
        "mode": result.policy.mode.value if result.policy else None,
        "inferred_mode": result.inferred_mode,
        "checkpoint_count": result.checkpoint_count,
        "start_commit": session.start_commit[:12],
        "start_branch": session.start_branch,
        "spec_path": str(session.spec_path),
    }
    _emit(payload, json_output)


# ── doctor ───────────────────────────────────────────────────────────


@app.command()
def doctor(
    project_root: str | None = typer.Option(
        None, "--project-root", help="Absolute path to the project root."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Diagnose the Autopilot installation and state. (Read-only)"""
    from cortex.autopilot.doctor import run_diagnosis

    root = _resolve_root(project_root)
    report = run_diagnosis(root)
    checks = [
        {"name": c.name, "ok": c.ok, "detail": c.detail, "action": c.action} for c in report.checks
    ]
    payload: dict[str, object] = {
        "project_root": str(root),
        "ok": report.ok,
        "checks": checks,
        "warnings": report.warnings,
    }
    _emit(payload, json_output)


# ── install / uninstall ─────────────────────────────────────────────
# Removed in Fase 04 cleanup. Use ``cortex session hooks install --ide <name>``
# and ``cortex session hooks uninstall --ide <name>`` — see
# ``cortex/cli/session.py`` (Phase 03 / T3.10).
