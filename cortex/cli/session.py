"""``cortex session`` — user-facing CLI for the Session primitive.

Sub-commands:
    current   — id of the active session (or "no active session")
    list      — list sessions, optionally filtered by status
    show      — full detail of one session (defaults to the active one)
    diff      — ``git diff start_commit..(end_commit|HEAD)`` for the session
    switch    — change the active session pointer
    abandon   — close a session as ABANDONED with a reason

All commands accept ``--project-root <path>`` (defaults to CWD) so that
they can be exercised from a tmpdir in tests, and ``--json`` for
machine-readable output suitable for piping into other tools.

The CLI talks directly to :class:`SessionService` (it does NOT spin up the
full :class:`AgentMemory` façade) because Session management does not need
the vault, the embeddings, the retriever, etc. This keeps ``cortex session``
fast and usable even in repos where Cortex is only partially configured.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from cortex.session import (
    CheckpointSource,
    SessionRecord,
    SessionStatus,
    TaskStatus,
)
from cortex.session.errors import SessionError, SessionNotFound
from cortex.session.git import GitError
from cortex.session.hooks import HookInstaller, default_installer
from cortex.session.service import SessionService
from cortex.session.storage import SessionStorage
from cortex.workspace.layout import WorkspaceLayout

session_app = typer.Typer(
    name="session",
    help="Manage the Session primitive (Pluggable Middle architecture).",
    no_args_is_help=True,
)

# Pre-build the Option default. Used as the function-signature default below;
# typer reads ``default`` and ``param_decls`` from it without conflicting with
# the ``Annotated[...]`` pattern (mixing both leads to "isidentifier" parse
# errors deep in click).
_PROJECT_ROOT_HELP = "Path to the Cortex project root (defaults to current directory)."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_service(project_root: Path | None) -> SessionService:
    """Resolve the layout and construct a ``SessionService``."""
    layout = WorkspaceLayout.discover(project_root or Path.cwd())
    storage = SessionStorage(layout.sessions_dir)
    return SessionService(storage, repo_root=layout.repo_root)


def _record_summary(record: SessionRecord) -> dict[str, object]:
    """Reduced representation used by the JSON output of ``list``."""
    return {
        "session_id": record.session_id,
        "status": record.status.value,
        "mode": record.mode.value,
        "opened_at": record.opened_at.isoformat(),
        "closed_at": record.closed_at.isoformat() if record.closed_at else None,
        "checkpoint_count": len(record.checkpoints),
        "spec_summary": record.spec_summary,
    }


def _error_exit(message: str, code: int = 1) -> None:
    typer.echo(message, err=True)
    raise typer.Exit(code)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@session_app.command("current")
def current_command(
    project_root: Path | None = typer.Option(None, "--project-root", help=_PROJECT_ROOT_HELP),
    output_json: bool = typer.Option(False, "--json", help="Emit JSON instead of plain text."),
) -> None:
    """Print the id of the currently active Session (or a friendly message)."""
    service = _build_service(project_root)
    record = service.get_active()
    if record is None:
        if output_json:
            typer.echo(json.dumps({"session_id": None}))
        else:
            typer.echo("(no active session)")
        return
    if output_json:
        typer.echo(json.dumps({"session_id": record.session_id}))
    else:
        typer.echo(record.session_id)


@session_app.command("list")
def list_command(
    status: str | None = typer.Option(
        None,
        "--status",
        help="Filter by status (open / closed / handoff / abandoned).",
    ),
    project_root: Path | None = typer.Option(None, "--project-root", help=_PROJECT_ROOT_HELP),
    output_json: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """List Sessions on disk, newest first."""
    service = _build_service(project_root)
    filter_status: SessionStatus | None = None
    if status is not None:
        try:
            filter_status = SessionStatus(status)
        except ValueError:
            _error_exit(
                f"Invalid status {status!r}. Must be one of: "
                f"{', '.join(s.value for s in SessionStatus)}"
            )
    records = service.list(filter_status)
    records.sort(key=lambda r: r.opened_at, reverse=True)
    active_record = service.get_active()
    active_id = active_record.session_id if active_record else None

    if output_json:
        typer.echo(json.dumps([_record_summary(r) for r in records], ensure_ascii=False))
        return

    if not records:
        typer.echo("(no sessions on disk)")
        return

    console = Console()
    table = Table(title=None, show_header=True, header_style="bold")
    table.add_column("", width=2)
    table.add_column("ID")
    table.add_column("STATUS")
    table.add_column("MODE")
    table.add_column("OPENED")
    table.add_column("CHECKPOINTS", justify="right")
    table.add_column("SUMMARY")
    for r in records:
        marker = "[bold cyan]►[/bold cyan]" if r.session_id == active_id else ""
        table.add_row(
            marker,
            r.session_id,
            r.status.value,
            r.mode.value,
            r.opened_at.strftime("%Y-%m-%d %H:%M"),
            str(len(r.checkpoints)),
            r.spec_summary[:60],
        )
    console.print(table)
    if active_id is not None:
        console.print(f"[dim]► = active session ({active_id})[/dim]")


@session_app.command("show")
def show_command(
    session_id: str | None = typer.Argument(
        None, help="Session id (defaults to the active session)."
    ),
    project_root: Path | None = typer.Option(None, "--project-root", help=_PROJECT_ROOT_HELP),
    output_json: bool = typer.Option(False, "--json", help="Emit the raw SessionRecord as JSON."),
    watch: bool = typer.Option(
        False,
        "--watch",
        help=(
            "Open the live TUI focused on this session (or the active one). "
            "Same behaviour as `cortex session watch [ID]`."
        ),
    ),
    refresh: float = typer.Option(
        1.5,
        "--refresh",
        help="Refresh interval in seconds (only meaningful with --watch).",
    ),
) -> None:
    """Print the full detail of one Session."""
    if watch:
        if output_json:
            _error_exit("--watch is not compatible with --json.")
        _run_watch_tui(project_root, refresh=refresh, focus_session_id=session_id)
        return

    service = _build_service(project_root)
    record = _resolve_record(service, session_id)

    if output_json:
        typer.echo(json.dumps(record.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return

    console = Console()
    console.print(f"[bold]Session:[/bold] {record.session_id}")
    console.print(f"  status:      [bold]{record.status.value}[/bold]")
    console.print(f"  mode:        {record.mode.value}")
    console.print(f"  spec:        {record.spec_path}")
    console.print(f"  summary:     {record.spec_summary}")
    console.print(f"  opened:      {record.opened_at.isoformat()}")
    console.print(f"  branch:      {record.start_branch}")
    console.print(f"  start commit:{record.start_commit}")
    if record.closed_at is not None:
        console.print(f"  closed:      {record.closed_at.isoformat()}")
        console.print(f"  end commit:  {record.end_commit}")
        console.print(
            f"  decision:    {record.documenter_decision and record.documenter_decision.value}"
        )

    if record.checkpoints:
        console.print()
        table = Table(title="Checkpoints", show_header=True, header_style="bold")
        table.add_column("TIMESTAMP")
        table.add_column("SOURCE")
        table.add_column("VERIFIED", justify="right")
        table.add_column("ARTIFACTS", justify="right")
        table.add_column("NOTE")
        for cp in record.checkpoints:
            table.add_row(
                cp.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                cp.source.value,
                str(len(cp.verified_claims)),
                str(len(cp.artifacts_touched)),
                cp.note[:60],
            )
        console.print(table)
    else:
        console.print()
        console.print("[dim](no checkpoints)[/dim]")

    if record.session_note_path is not None:
        console.print(f"\n[dim]session note:[/dim] {record.session_note_path}")
    if record.adrs_created:
        console.print(f"[dim]ADRs created:[/dim] {len(record.adrs_created)}")


_REFRESH_MIN = 0.5
_REFRESH_MAX = 30.0


def _run_watch_tui(
    project_root: Path | None,
    *,
    refresh: float,
    focus_session_id: str | None,
) -> None:
    """Shared entry point for ``session watch`` and ``session show --watch``."""
    if not (_REFRESH_MIN <= refresh <= _REFRESH_MAX):
        _error_exit(
            f"--refresh must be between {_REFRESH_MIN} and {_REFRESH_MAX} seconds."
        )
    service = _build_service(project_root)
    # Local import keeps the CLI import-time cheap when the user only
    # runs static subcommands like ``cortex session list``.
    from cortex.cli.session_tui import run_tui

    run_tui(
        service,
        project_root=(project_root or Path.cwd()).resolve(),
        refresh_interval=refresh,
        focus_session_id=focus_session_id,
    )


@session_app.command("watch")
def watch_command(
    session_id: str | None = typer.Argument(
        None,
        help="Optional session id to focus on (defaults to the active session).",
    ),
    refresh: float = typer.Option(
        1.5,
        "--refresh",
        help=(
            f"Refresh interval in seconds (min {_REFRESH_MIN}, max {_REFRESH_MAX})."
        ),
    ),
    project_root: Path | None = typer.Option(
        None, "--project-root", help=_PROJECT_ROOT_HELP
    ),
) -> None:
    """Open a live TUI view of the active (or named) Session.

    Refreshes every ``--refresh`` seconds. Press Ctrl+C to exit. Use
    ``cortex finish-session`` to close the underlying Session.
    """
    _run_watch_tui(project_root, refresh=refresh, focus_session_id=session_id)


@session_app.command("diff")
def diff_command(
    session_id: str | None = typer.Argument(
        None, help="Session id (defaults to the active session)."
    ),
    project_root: Path | None = typer.Option(None, "--project-root", help=_PROJECT_ROOT_HELP),
) -> None:
    """Print ``git diff <start_commit>..<end_ref>`` for the Session."""
    service = _build_service(project_root)
    record = _resolve_record(service, session_id)
    try:
        text = service.compute_diff(record.session_id)
    except GitError as exc:
        _error_exit(f"git error: {exc}")
        return  # pragma: no cover — _error_exit always raises
    if not text:
        typer.echo("(no diff — start_commit equals end_ref)")
    else:
        typer.echo(text)


@session_app.command("switch")
def switch_command(
    session_id: str = typer.Argument(..., help="Session id to mark as active."),
    project_root: Path | None = typer.Option(None, "--project-root", help=_PROJECT_ROOT_HELP),
) -> None:
    """Set ``session_id`` as the active session. It must exist and be OPEN."""
    service = _build_service(project_root)
    try:
        service.set_active(session_id)
    except SessionError as exc:
        _error_exit(str(exc))
        return  # pragma: no cover
    typer.echo(f"active session: {session_id}")


@session_app.command("checkpoint")
def checkpoint_command(
    source: str = typer.Option(
        "manual",
        "--source",
        help="CheckpointSource value (e.g. manual, ide-hook, cortex-SDDwork).",
    ),
    note: str = typer.Option(
        "", "--note", help="Free-form note carried into the next step."
    ),
    verified_claim: list[str] = typer.Option(
        [], "--verified-claim", help="A verified claim (repeatable)."
    ),
    unverified_claim: list[str] = typer.Option(
        [], "--unverified-claim", help="A claim not yet verified (repeatable)."
    ),
    artifact: list[str] = typer.Option(
        [], "--artifact", help="Artifact path touched (repeatable)."
    ),
    session_id: str | None = typer.Option(
        None,
        "--session-id",
        help="Explicit session id (defaults to the active session).",
    ),
    project_root: Path | None = typer.Option(None, "--project-root", help=_PROJECT_ROOT_HELP),
    output_json: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Append a checkpoint to the active session.

    This is the command invoked by the IDE hooks installed via
    ``cortex session hooks install --ide <name>``.
    """
    service = _build_service(project_root)
    try:
        cp_source = CheckpointSource(source)
    except ValueError:
        valid = ", ".join(s.value for s in CheckpointSource)
        _error_exit(f"Invalid --source {source!r}; valid: {valid}")
        return  # pragma: no cover
    record = _resolve_record(service, session_id)
    try:
        updated = service.checkpoint(
            record.session_id,
            source=cp_source,
            verified_claims=verified_claim,
            unverified_claims=unverified_claim,
            artifacts_touched=artifact,
            note=note,
        )
    except SessionError as exc:
        _error_exit(str(exc))
        return  # pragma: no cover
    if output_json:
        typer.echo(
            json.dumps(
                {
                    "session_id": updated.session_id,
                    "checkpoint_count": len(updated.checkpoints),
                    "source": cp_source.value,
                }
            )
        )
        return
    typer.echo(
        f"checkpoint #{len(updated.checkpoints)} appended "
        f"(source={cp_source.value}) to {updated.session_id}"
    )


@session_app.command("abandon")
def abandon_command(
    session_id: str = typer.Argument(..., help="Session id to abandon."),
    reason: str = typer.Option(
        ..., "--reason", help="Reason for abandonment (recorded as a checkpoint)."
    ),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt."),
    project_root: Path | None = typer.Option(None, "--project-root", help=_PROJECT_ROOT_HELP),
) -> None:
    """Close a session as ABANDONED. No session note is created."""
    if not yes:
        confirmed = typer.confirm(
            f"Abandon session {session_id!r} with reason: {reason!r}?",
            default=False,
        )
        if not confirmed:
            typer.echo("aborted.")
            raise typer.Exit(0)
    service = _build_service(project_root)
    try:
        record = service.abandon(session_id, reason=reason)
    except SessionError as exc:
        _error_exit(str(exc))
        return  # pragma: no cover
    typer.echo(f"abandoned session: {record.session_id}")


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _resolve_record(service: SessionService, session_id: str | None) -> SessionRecord:
    """Load ``session_id`` if provided, otherwise the active session."""
    if session_id is None:
        record = service.get_active()
        if record is None:
            _error_exit("No active session. Pass an explicit session id.")
            raise typer.Exit(1)  # pragma: no cover — _error_exit raises
        return record
    try:
        return service.get(session_id)
    except SessionNotFound:
        _error_exit(f"Session not found: {session_id}")
        raise typer.Exit(1) from None  # pragma: no cover


# ---------------------------------------------------------------------------
# ``cortex session task ...`` subapp (Pluggable Middle Phase 09.C)
# ---------------------------------------------------------------------------

task_app = typer.Typer(
    name="task",
    help="Manage granular tasks attached to a Session (Pluggable Middle Phase 09.C).",
    no_args_is_help=True,
)
session_app.add_typer(task_app, name="task")


def _resolve_task_session(
    service: SessionService, session_id: str | None
) -> SessionRecord:
    """Pick the requested or active Session for the task subcommands."""
    if session_id is None:
        record = service.get_active()
        if record is None:
            _error_exit("No active session. Pass --session-id explicitly.")
            raise typer.Exit(1)  # pragma: no cover — _error_exit raises
        return record
    try:
        return service.get(session_id)
    except SessionNotFound:
        _error_exit(f"Session not found: {session_id}")
        raise typer.Exit(1) from None  # pragma: no cover


@task_app.command("list")
def task_list_command(
    session_id: str | None = typer.Option(
        None,
        "--session-id",
        help="Session id (defaults to the active session).",
    ),
    status: str | None = typer.Option(
        None,
        "--status",
        help="Filter by status (pending|in-progress|done|skipped|blocked).",
    ),
    project_root: Path | None = typer.Option(
        None, "--project-root", help=_PROJECT_ROOT_HELP
    ),
    output_json: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """List tasks attached to a Session."""
    service = _build_service(project_root)
    record = _resolve_task_session(service, session_id)
    filter_status: TaskStatus | None = None
    if status is not None:
        try:
            filter_status = TaskStatus(status)
        except ValueError:
            _error_exit(
                f"Invalid --status {status!r}. Must be one of: "
                f"{', '.join(s.value for s in TaskStatus)}"
            )
    tasks = service.list_tasks(record.session_id, status=filter_status)

    if output_json:
        typer.echo(
            json.dumps(
                [t.model_dump(mode="json") for t in tasks],
                ensure_ascii=False,
            )
        )
        return

    if not tasks:
        typer.echo("(no tasks)")
        return

    console = Console()
    table = Table(show_header=True, header_style="bold")
    table.add_column("ID")
    table.add_column("STATUS")
    table.add_column("DESCRIPTION")
    table.add_column("FILES")
    for t in tasks:
        table.add_row(
            t.id,
            t.status.value,
            t.description[:60],
            ", ".join(t.files_in_scope[:3])
            + (f" (+{len(t.files_in_scope) - 3})" if len(t.files_in_scope) > 3 else ""),
        )
    console.print(table)


def _update_task_status_cli(
    *,
    task_id: str,
    new_status: TaskStatus,
    session_id: str | None,
    note: str,
    project_root: Path | None,
    output_json: bool,
) -> None:
    service = _build_service(project_root)
    record = _resolve_task_session(service, session_id)
    try:
        updated = service.update_task_status(
            record.session_id,
            task_id,
            new_status,
            note=note,
        )
    except (SessionError, ValueError) as exc:
        _error_exit(str(exc))
        return  # pragma: no cover
    if output_json:
        typer.echo(
            json.dumps(
                {
                    "session_id": updated.session_id,
                    "task_id": task_id,
                    "status": new_status.value,
                },
                ensure_ascii=False,
            )
        )
        return
    typer.echo(f"{task_id} → {new_status.value}")


@task_app.command("done")
def task_done_command(
    task_id: str = typer.Argument(..., help="Task id (e.g. T1.2)."),
    note: str = typer.Option("", "--note", help="Optional note recorded on the task."),
    session_id: str | None = typer.Option(
        None, "--session-id", help="Session id (defaults to active)."
    ),
    project_root: Path | None = typer.Option(None, "--project-root", help=_PROJECT_ROOT_HELP),
    output_json: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Mark a task as ``done``."""
    _update_task_status_cli(
        task_id=task_id,
        new_status=TaskStatus.DONE,
        session_id=session_id,
        note=note,
        project_root=project_root,
        output_json=output_json,
    )


@task_app.command("in-progress")
def task_in_progress_command(
    task_id: str = typer.Argument(..., help="Task id."),
    note: str = typer.Option("", "--note"),
    session_id: str | None = typer.Option(None, "--session-id"),
    project_root: Path | None = typer.Option(None, "--project-root", help=_PROJECT_ROOT_HELP),
    output_json: bool = typer.Option(False, "--json"),
) -> None:
    """Mark a task as ``in-progress``."""
    _update_task_status_cli(
        task_id=task_id,
        new_status=TaskStatus.IN_PROGRESS,
        session_id=session_id,
        note=note,
        project_root=project_root,
        output_json=output_json,
    )


@task_app.command("skip")
def task_skip_command(
    task_id: str = typer.Argument(..., help="Task id."),
    reason: str = typer.Option(..., "--reason", help="Why the task is being skipped."),
    session_id: str | None = typer.Option(None, "--session-id"),
    project_root: Path | None = typer.Option(None, "--project-root", help=_PROJECT_ROOT_HELP),
    output_json: bool = typer.Option(False, "--json"),
) -> None:
    """Mark a task as ``skipped`` (with mandatory reason)."""
    _update_task_status_cli(
        task_id=task_id,
        new_status=TaskStatus.SKIPPED,
        session_id=session_id,
        note=reason,
        project_root=project_root,
        output_json=output_json,
    )


@task_app.command("block")
def task_block_command(
    task_id: str = typer.Argument(..., help="Task id."),
    reason: str = typer.Option(..., "--reason", help="Why the task is blocked."),
    session_id: str | None = typer.Option(None, "--session-id"),
    project_root: Path | None = typer.Option(None, "--project-root", help=_PROJECT_ROOT_HELP),
    output_json: bool = typer.Option(False, "--json"),
) -> None:
    """Mark a task as ``blocked`` (with mandatory reason)."""
    _update_task_status_cli(
        task_id=task_id,
        new_status=TaskStatus.BLOCKED,
        session_id=session_id,
        note=reason,
        project_root=project_root,
        output_json=output_json,
    )


# ---------------------------------------------------------------------------
# ``cortex session hooks ...`` subapp (T3.10 — Pluggable Middle Fase 03)
# ---------------------------------------------------------------------------

hooks_app = typer.Typer(
    name="hooks",
    help="Install / inspect IDE hooks for the Observed mode.",
    no_args_is_help=True,
)
session_app.add_typer(hooks_app, name="hooks")


def _resolve_installer() -> HookInstaller:
    return default_installer()


def _resolve_target_dir(project_root: Path | None) -> Path:
    return (project_root or Path.cwd()).resolve()


@hooks_app.command("list")
def hooks_list_command(
    project_root: Path | None = typer.Option(
        None, "--project-root", help=_PROJECT_ROOT_HELP
    ),
    output_json: bool = typer.Option(
        False, "--json", help="Emit JSON instead of a table."
    ),
) -> None:
    """List the bundled IDE adapters and report their current install status."""
    installer = _resolve_installer()
    target = _resolve_target_dir(project_root)
    statuses = installer.status_all(target)
    if output_json:
        typer.echo(
            json.dumps(
                [
                    {
                        "ide": s.ide,
                        "installed": s.installed,
                        "supported": s.supported,
                        "detail": s.detail,
                    }
                    for s in statuses
                ],
                ensure_ascii=False,
            )
        )
        return
    console = Console()
    table = Table(show_header=True, header_style="bold")
    table.add_column("IDE")
    table.add_column("INSTALLED", justify="center")
    table.add_column("SUPPORTED", justify="center")
    table.add_column("DETAIL")
    for s in statuses:
        table.add_row(
            s.ide,
            "✓" if s.installed else "—",
            "✓" if s.supported else "—",
            s.detail,
        )
    console.print(table)


@hooks_app.command("install")
def hooks_install_command(
    ide: str = typer.Option(
        ..., "--ide", help="Adapter name (use `cortex session hooks list` to see options)."
    ),
    project_root: Path | None = typer.Option(
        None, "--project-root", help=_PROJECT_ROOT_HELP
    ),
    output_json: bool = typer.Option(
        False, "--json", help="Emit JSON instead of plain text."
    ),
) -> None:
    """Install the requested IDE hook under the project root."""
    installer = _resolve_installer()
    target = _resolve_target_dir(project_root)
    try:
        result = installer.install(ide, target)
    except KeyError as exc:
        _error_exit(str(exc))
        return  # pragma: no cover
    except ValueError as exc:
        _error_exit(f"Could not install {ide}: {exc}")
        return  # pragma: no cover
    if output_json:
        typer.echo(
            json.dumps(
                {
                    "ide": result.ide,
                    "installed": result.installed,
                    "modified_paths": [str(p) for p in result.modified_paths],
                    "message": result.message,
                },
                ensure_ascii=False,
            )
        )
        return
    marker = "✓" if result.installed else "✗"
    typer.echo(f"{marker} {result.ide}: {result.message}")
    for p in result.modified_paths:
        typer.echo(f"  modified: {p}")


@hooks_app.command("uninstall")
def hooks_uninstall_command(
    ide: str = typer.Option(..., "--ide", help="Adapter name."),
    project_root: Path | None = typer.Option(
        None, "--project-root", help=_PROJECT_ROOT_HELP
    ),
    output_json: bool = typer.Option(
        False, "--json", help="Emit JSON instead of plain text."
    ),
) -> None:
    """Uninstall the requested IDE hook from the project root."""
    installer = _resolve_installer()
    target = _resolve_target_dir(project_root)
    try:
        result = installer.uninstall(ide, target)
    except KeyError as exc:
        _error_exit(str(exc))
        return  # pragma: no cover
    if output_json:
        typer.echo(
            json.dumps(
                {
                    "ide": result.ide,
                    "uninstalled": result.uninstalled,
                    "removed_paths": [str(p) for p in result.removed_paths],
                    "message": result.message,
                },
                ensure_ascii=False,
            )
        )
        return
    marker = "✓" if result.uninstalled else "—"
    typer.echo(f"{marker} {result.ide}: {result.message}")
    for p in result.removed_paths:
        typer.echo(f"  removed: {p}")


@hooks_app.command("status")
def hooks_status_command(
    ide: str | None = typer.Option(
        None, "--ide", help="Adapter name (omit to report all known adapters)."
    ),
    project_root: Path | None = typer.Option(
        None, "--project-root", help=_PROJECT_ROOT_HELP
    ),
    output_json: bool = typer.Option(
        False, "--json", help="Emit JSON instead of plain text."
    ),
) -> None:
    """Report the install status of one or all IDE adapters."""
    installer = _resolve_installer()
    target = _resolve_target_dir(project_root)
    if ide is None:
        statuses = installer.status_all(target)
    else:
        try:
            statuses = [installer.status(ide, target)]
        except KeyError as exc:
            _error_exit(str(exc))
            return  # pragma: no cover
    if output_json:
        typer.echo(
            json.dumps(
                [
                    {
                        "ide": s.ide,
                        "installed": s.installed,
                        "supported": s.supported,
                        "detail": s.detail,
                    }
                    for s in statuses
                ],
                ensure_ascii=False,
            )
        )
        return
    for s in statuses:
        marker = "✓" if s.installed else "—"
        typer.echo(f"{marker} {s.ide}: {s.detail}")
