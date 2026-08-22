"""``cortex session watch`` — live TUI for the Session primitive.

Phase 06 of the Pluggable Middle architecture. The TUI is **read-only**:
it polls ``.cortex/sessions/`` every ``refresh_interval`` seconds and
re-renders a ``rich.Layout`` with the active session, recent
checkpoints, a truncated diff preview, the verification summary, and a
sidebar with recent sessions. ``Ctrl+C`` exits cleanly.

Design:
    * :class:`SessionTuiState` is a frozen snapshot. The renderer is a
      **pure function** ``state → rich.Layout`` so it can be unit-tested
      against ``Console(file=StringIO(), force_terminal=True, …)``
      without spinning up a TTY.
    * :func:`run_tui` is the live loop. It is **not** unit-tested —
      ``tests/e2e/test_session_tui_smoke.py`` covers the subprocess
      behaviour end-to-end.
    * No threads. Single-threaded polling at 1.5s by default. No mouse,
      no keyboard input. Out of scope for v1 (see the phase plan §2).
    * Layout breakpoints: ≥ 100 cols full 3-column layout; ≥ 70 cols
      2-column (sidebar dropped); else vertical stack.
    * Glyphs route through :mod:`cortex.cli._unicode_fallback` so the
      TUI degrades gracefully on legacy Windows consoles.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from cortex.cli._unicode_fallback import glyph
from cortex.session import git as git_module
from cortex.session.models import (
    SessionMode,
    SessionRecord,
    SessionStatus,
    VerificationHookResult,
)
from cortex.session.service import SessionService

if TYPE_CHECKING:
    from cortex.session.models import Checkpoint

logger = logging.getLogger(__name__)

_DIFF_PREVIEW_MAX_LINES = 8
_CHECKPOINTS_VISIBLE = 5
_RECENT_SIDEBAR_VISIBLE = 5
_SIDEBAR_REFRESH_EVERY = 10  # ticks
_NOTE_PREVIEW_CHARS = 40

# Layout breakpoints. Below 70 cols we stack vertically.
_BREAKPOINT_FULL = 100
_BREAKPOINT_MEDIUM = 70


# ---------------------------------------------------------------------------
# State snapshot
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionTuiState:
    """Immutable snapshot the renderer consumes.

    Built once at start, rebuilt on every detected change. The renderer
    never reaches back into the storage; everything it needs is here.
    """

    active_session: SessionRecord | None
    recent_sessions: list[SessionRecord] = field(default_factory=list)
    diff_preview: str = ""
    refresh_tick: int = 0
    repo_root: Path = field(default_factory=Path.cwd)
    project_name: str = ""
    branch: str = ""
    documenter_mode: str = "auto"
    refresh_interval: float = 1.5
    refreshed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    total_open: int = 0
    total_closed: int = 0
    total_handoff: int = 0
    total_abandoned: int = 0
    diff_error: str = ""


# ---------------------------------------------------------------------------
# Pure helpers — formatting
# ---------------------------------------------------------------------------


def _format_relative(then: datetime, *, now: datetime | None = None) -> str:
    """Return a short relative-time string for ``then``.

    Examples: ``"just now"``, ``"5s ago"``, ``"12m ago"``, ``"2h 14m ago"``,
    ``"1d 4h ago"``. Bounded vocabulary so the column never widens.
    """
    if then.tzinfo is None:
        then = then.replace(tzinfo=UTC)
    now = now or datetime.now(UTC)
    delta = now - then
    seconds = int(delta.total_seconds())
    if seconds < 5:
        return "just now"
    if seconds < 60:
        return f"{seconds}s ago"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m ago"
    hours, mm = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {mm}m ago" if mm else f"{hours}h ago"
    days, hh = divmod(hours, 24)
    return f"{days}d {hh}h ago" if hh else f"{days}d ago"


def _format_duration_ms(ms: int) -> str:
    """Format a duration in ms as ``"824ms"``, ``"5.2s"`` or ``"2m 4s"``."""
    if ms < 1000:
        return f"{ms}ms"
    seconds = ms / 1000.0
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, rem = divmod(int(seconds), 60)
    return f"{minutes}m {rem}s"


def _safe_mtime(path: Path) -> float | None:
    """Return ``path.stat().st_mtime`` or None when the path is missing."""
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def _truncate(text: str, length: int) -> str:
    """Truncate to ``length`` characters, append an ellipsis when cut."""
    if len(text) <= length:
        return text
    return text[: max(0, length - 1)].rstrip() + "…"


def _verification_status_label(
    result: VerificationHookResult,
    *,
    console: Console,
) -> str:
    """Return ``"✓ name (5.2s)"`` style label for a verification result."""
    marker = glyph("check" if result.passed else "fail", console=console)
    duration = _format_duration_ms(result.duration_ms)
    return f"{marker} {result.name} ({duration})"


# ---------------------------------------------------------------------------
# Pure render functions
# ---------------------------------------------------------------------------


def _render_header(state: SessionTuiState, *, console: Console) -> Panel:
    """One-line top banner: project · branch · mode · counts · refreshed."""
    parts = [
        Text(state.project_name or "cortex", style="bold"),
        Text(" · ", style="dim"),
        Text(state.branch or "<no git>", style="cyan"),
        Text(" · ", style="dim"),
        Text(f"documenter: {state.documenter_mode}", style="magenta"),
        Text(" · ", style="dim"),
        Text(f"{state.total_open} open", style="green" if state.total_open else "dim"),
        Text(" · ", style="dim"),
        Text(f"{state.total_closed} closed", style="dim"),
    ]
    if state.total_handoff:
        parts.extend([Text(" · ", style="dim"), Text(f"{state.total_handoff} handoff", style="yellow")])
    line = Text.assemble(*parts)
    line.append("    ", style="dim")
    line.append(
        f"refreshed: {state.refreshed_at.astimezone().strftime('%H:%M:%S')}",
        style="dim",
    )
    return Panel(line, padding=(0, 1), border_style="dim")


def _render_footer(state: SessionTuiState) -> Panel:
    """One-line bottom hint: refresh interval + how to quit."""
    text = Text.assemble(
        ("Watching", "bold"),
        (" · ", "dim"),
        (f"refresh every {state.refresh_interval:g}s", "dim"),
        (" · ", "dim"),
        ("Ctrl+C to quit", "bold yellow"),
        (" · ", "dim"),
        ("Use ", "dim"),
        ("cortex finish-session", "cyan"),
        (" to close.", "dim"),
    )
    return Panel(text, padding=(0, 1), border_style="dim")


def _render_no_active_session_panel(state: SessionTuiState, *, console: Console) -> Panel:
    """Placeholder when there is no active Session yet."""
    arrow = glyph("arrow_right", console=console) or ">"
    body = Text()
    body.append("NO ACTIVE SESSION\n\n", style="bold yellow")
    body.append("Open one with:\n", style="dim")
    body.append(
        f"  {arrow} cortex create-spec --title \"...\" --goal \"...\" \\\n",
        style="cyan",
    )
    body.append(
        "        --verification-hook 'name=t;command=...'\n\n",
        style="cyan",
    )
    body.append("Or pick an existing one:\n", style="dim")
    body.append(f"  {arrow} cortex session list\n", style="cyan")
    body.append(f"  {arrow} cortex session switch <ID>\n\n", style="cyan")
    body.append("Watching for a new session… (Ctrl+C to quit)", style="dim italic")
    return Panel(body, title="cortex session watch", border_style="yellow", padding=(1, 2))


def _render_active_session_panel(state: SessionTuiState, *, console: Console) -> Panel:
    """Identity + opened_at + verification status block for the active session."""
    record = state.active_session
    assert record is not None  # caller guarantees this
    now = datetime.now(UTC)

    is_unknown_mode = record.mode is SessionMode.UNKNOWN
    inferred_mode = (
        SessionService.infer_mode(record.checkpoints).value
        if is_unknown_mode
        else record.mode.value
    )

    lines: list[Text] = []
    lines.append(Text.assemble(("id      : ", "dim"), (record.session_id, "bold")))
    lines.append(
        Text.assemble(
            ("status  : ", "dim"),
            (record.status.value, "bold green" if record.status is SessionStatus.OPEN else "bold"),
        )
    )
    lines.append(
        Text.assemble(
            ("mode    : ", "dim"),
            (inferred_mode, "magenta"),
            (" (inferred)" if is_unknown_mode else "", "dim"),
        )
    )
    lines.append(Text.assemble(("spec    : ", "dim"), (str(record.spec_path), "cyan")))
    summary_truncated = _truncate(record.spec_summary or "(no summary)", 80)
    lines.append(Text.assemble(("summary : ", "dim"), (summary_truncated, "")))
    lines.append(Text.assemble(("branch  : ", "dim"), (record.start_branch, "cyan")))
    lines.append(Text.assemble(("start   : ", "dim"), (record.start_commit[:8], "")))
    lines.append(
        Text.assemble(("opened  : ", "dim"), (_format_relative(record.opened_at, now=now), "yellow"))
    )

    # Verification block.
    if record.verification_results:
        lines.append(Text())
        lines.append(Text(f"── verification ({len(record.verification_results)}) ──", style="dim"))
        for r in record.verification_results:
            lines.append(Text(_verification_status_label(r, console=console)))
    else:
        # Show hooks declared in spec if available; otherwise a "not run" hint.
        lines.append(Text())
        marker = glyph("pending", console=console)
        lines.append(Text(f"{marker} verification not yet run", style="dim italic"))

    body = Group(*lines)
    return Panel(body, title="ACTIVE SESSION", border_style="green", padding=(0, 1))


def _checkpoint_row(
    cp: Checkpoint,
    *,
    now: datetime,
    console: Console,
) -> tuple[str, str, str, str, str]:
    """Build one row for the checkpoints table."""
    ts = _format_relative(cp.timestamp, now=now)
    source = cp.source.value
    if len(source) > 22:
        source = source[:21] + "…"
    check = glyph("check", console=console) or "OK"
    verified = f"{check} {len(cp.verified_claims)}" if cp.verified_claims else "0"
    files = ", ".join(cp.artifacts_touched[:2])
    if len(cp.artifacts_touched) > 2:
        files = f"{files} (+{len(cp.artifacts_touched) - 2})"
    if not files:
        files = "—"
    files = _truncate(files, 30)
    note = _truncate(cp.note, _NOTE_PREVIEW_CHARS) if cp.note else "—"
    return ts, source, verified, files, note


def _render_checkpoints_panel(state: SessionTuiState, *, console: Console) -> Panel:
    """Table of the most recent checkpoints (newest first)."""
    record = state.active_session
    assert record is not None
    now = datetime.now(UTC)

    if not record.checkpoints:
        return Panel(
            Text("(no checkpoints yet)", style="dim italic"),
            title="CHECKPOINTS",
            border_style="blue",
            padding=(1, 2),
        )

    total = len(record.checkpoints)
    visible = list(reversed(record.checkpoints))[:_CHECKPOINTS_VISIBLE]

    table = Table(show_header=True, header_style="bold blue", box=None, expand=True)
    table.add_column("TIME", style="yellow", no_wrap=True)
    table.add_column("SOURCE", style="cyan", no_wrap=True)
    table.add_column("VERIF", justify="right", no_wrap=True)
    table.add_column("FILES", style="dim", no_wrap=True)
    table.add_column("NOTE")
    for cp in visible:
        table.add_row(*_checkpoint_row(cp, now=now, console=console))

    title = f"CHECKPOINTS ({total})"
    if total > _CHECKPOINTS_VISIBLE:
        footer = Text(f"(+ {total - _CHECKPOINTS_VISIBLE} earlier)", style="dim italic")
        body = Group(table, Text(), footer)
    else:
        body = Group(table)
    return Panel(body, title=title, border_style="blue", padding=(0, 1))


def _render_diff_panel(state: SessionTuiState) -> Panel:
    """Truncated diff preview (first N lines + "more" footer)."""
    if state.diff_error:
        return Panel(
            Text(f"(diff unavailable: {state.diff_error})", style="dim italic"),
            title="DIFF PREVIEW",
            border_style="blue",
            padding=(0, 1),
        )
    if not state.diff_preview:
        return Panel(
            Text("(no diff — start_commit equals end_ref)", style="dim italic"),
            title="DIFF PREVIEW",
            border_style="blue",
            padding=(0, 1),
        )

    raw_lines = state.diff_preview.splitlines()
    visible = raw_lines[:_DIFF_PREVIEW_MAX_LINES]
    extra = len(raw_lines) - len(visible)

    body = Text()
    for line in visible:
        style = ""
        if line.startswith("+++") or line.startswith("---"):
            style = "bold"
        elif line.startswith("+"):
            style = "green"
        elif line.startswith("-"):
            style = "red"
        elif line.startswith("@@"):
            style = "cyan"
        body.append(line + "\n", style=style)
    if extra > 0:
        body.append(f"(+ {extra} more lines)", style="dim italic")

    return Panel(body, title="DIFF PREVIEW", border_style="blue", padding=(0, 1))


def _render_recent_sessions_panel(state: SessionTuiState, *, console: Console) -> Panel:
    """Sidebar with the last few sessions, active row highlighted."""
    now = datetime.now(UTC)
    arrow = glyph("arrow_right", console=console) or ">"
    active_id = state.active_session.session_id if state.active_session else None

    visible = state.recent_sessions[:_RECENT_SIDEBAR_VISIBLE]
    extra = max(0, len(state.recent_sessions) - len(visible))

    table = Table(show_header=True, header_style="bold", box=None, expand=True)
    table.add_column("", width=2)
    table.add_column("STATUS", no_wrap=True)
    table.add_column("AGE", style="yellow", no_wrap=True)
    table.add_column("ID")
    for r in visible:
        is_active = r.session_id == active_id
        prefix = f"[bold cyan]{arrow}[/bold cyan]" if is_active else ""
        status_style = "green" if r.status is SessionStatus.OPEN else "dim"
        table.add_row(
            prefix,
            Text(r.status.value, style="bold" if is_active else status_style),
            _format_relative(r.opened_at, now=now),
            Text(r.session_id, style="bold" if is_active else "dim"),
        )

    body: Group | Table
    if extra:
        body = Group(
            table,
            Text(),
            Text(f"(+ {extra} more — see `list`)", style="dim italic"),
        )
    else:
        body = table

    return Panel(body, title="RECENT SESSIONS", border_style="magenta", padding=(0, 1))


# ---------------------------------------------------------------------------
# Layout assembly
# ---------------------------------------------------------------------------


def render_layout(state: SessionTuiState, *, max_width: int, console: Console) -> Layout:
    """Build the full ``rich.Layout`` for the given state.

    Pure function — same input always produces the same output. Layout
    shape adapts to ``max_width``:
        - ≥ 100 cols → 3 columns (active | center | sidebar).
        - ≥ 70  cols → 2 columns (active | center; sidebar dropped).
        - <  70 cols → vertical stack.
    """
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3),
    )

    if state.active_session is None:
        # Placeholder takes over the whole body.
        layout["body"].update(_render_no_active_session_panel(state, console=console))
        layout["header"].update(_render_header(state, console=console))
        layout["footer"].update(_render_footer(state))
        return layout

    # Center column always stacks checkpoints over the diff preview.
    center = Layout(name="center")
    center.split_column(
        Layout(name="checkpoints", ratio=60),
        Layout(name="diff", ratio=40),
    )
    center["checkpoints"].update(_render_checkpoints_panel(state, console=console))
    center["diff"].update(_render_diff_panel(state))

    if max_width >= _BREAKPOINT_FULL:
        layout["body"].split_row(
            Layout(name="left", ratio=45),
            Layout(name="center_wrap", ratio=35),
            Layout(name="right", ratio=20),
        )
        layout["body"]["left"].update(_render_active_session_panel(state, console=console))
        layout["body"]["center_wrap"].update(center)
        layout["body"]["right"].update(_render_recent_sessions_panel(state, console=console))
    elif max_width >= _BREAKPOINT_MEDIUM:
        layout["body"].split_row(
            Layout(name="left", ratio=55),
            Layout(name="center_wrap", ratio=45),
        )
        layout["body"]["left"].update(_render_active_session_panel(state, console=console))
        layout["body"]["center_wrap"].update(center)
    else:
        layout["body"].split_column(
            Layout(name="left", ratio=50),
            Layout(name="center_wrap", ratio=50),
        )
        layout["body"]["left"].update(_render_active_session_panel(state, console=console))
        layout["body"]["center_wrap"].update(center)

    layout["header"].update(_render_header(state, console=console))
    layout["footer"].update(_render_footer(state))
    return layout


# ---------------------------------------------------------------------------
# State builder
# ---------------------------------------------------------------------------


def _build_state(
    service: SessionService,
    *,
    project_root: Path,
    focus_session_id: str | None,
    refresh_tick: int,
    refresh_interval: float,
    documenter_mode: str,
    previous_recent: list[SessionRecord] | None = None,
) -> SessionTuiState:
    """Snapshot everything the renderer needs at this tick.

    The sidebar listing is expensive on large vaults, so we only refresh
    it every ``_SIDEBAR_REFRESH_EVERY`` ticks; ``previous_recent`` lets
    us cheaply reuse the prior snapshot in between.
    """
    repo_root = project_root.resolve()
    project_name = repo_root.name or "cortex"

    try:
        branch = git_module.get_current_branch(repo_root)
    except Exception:  # noqa: BLE001 — degrade gracefully on missing git
        branch = ""

    if focus_session_id:
        try:
            active_record: SessionRecord | None = service.get(focus_session_id)
        except Exception:  # noqa: BLE001 — show placeholder if id is gone
            active_record = None
    else:
        active_record = service.get_active()

    # Sidebar refresh policy: full reload on tick 0 or every Nth tick;
    # otherwise reuse the previous snapshot.
    if (
        previous_recent is None
        or refresh_tick == 0
        or refresh_tick % _SIDEBAR_REFRESH_EVERY == 0
    ):
        try:
            all_records = service.list()
        except Exception:  # noqa: BLE001 — surface in the panel, not crash
            all_records = []
        all_records.sort(key=lambda r: r.opened_at, reverse=True)
        recent_sessions = all_records
    else:
        recent_sessions = list(previous_recent)

    # Counts always come from the latest cached snapshot.
    totals = {s: 0 for s in SessionStatus}
    for r in recent_sessions:
        totals[r.status] = totals.get(r.status, 0) + 1

    diff_preview = ""
    diff_error = ""
    if active_record is not None:
        try:
            diff_preview = service.compute_diff(active_record.session_id)
        except Exception as exc:  # noqa: BLE001 — render the message
            diff_error = type(exc).__name__

    return SessionTuiState(
        active_session=active_record,
        recent_sessions=recent_sessions,
        diff_preview=diff_preview,
        diff_error=diff_error,
        refresh_tick=refresh_tick,
        repo_root=repo_root,
        project_name=project_name,
        branch=branch,
        documenter_mode=documenter_mode,
        refresh_interval=refresh_interval,
        refreshed_at=datetime.now(UTC),
        total_open=totals.get(SessionStatus.OPEN, 0),
        total_closed=totals.get(SessionStatus.CLOSED, 0),
        total_handoff=totals.get(SessionStatus.HANDOFF, 0),
        total_abandoned=totals.get(SessionStatus.ABANDONED, 0),
    )


# ---------------------------------------------------------------------------
# Change detection (cheap polling)
# ---------------------------------------------------------------------------


def _snapshot_session_mtimes(service: SessionService) -> dict[str, float]:
    """Map session_id → mtime of its YAML file."""
    out: dict[str, float] = {}
    try:
        records = service.list()
    except Exception:  # noqa: BLE001
        return out
    for r in records:
        mt = _safe_mtime(service.path_for(r.session_id))
        if mt is not None:
            out[r.session_id] = mt
    return out


def _detect_changes(
    service: SessionService,
    *,
    prev_active_mtime: float | None,
    prev_session_mtimes: dict[str, float],
) -> tuple[bool, float | None, dict[str, float]]:
    """Return ``(changed, new_active_mtime, new_session_mtimes)``."""
    new_active = _safe_mtime(service.active_pointer_path())
    new_mtimes = _snapshot_session_mtimes(service)
    changed = new_active != prev_active_mtime or new_mtimes != prev_session_mtimes
    return changed, new_active, new_mtimes


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def _resolve_documenter_mode(project_root: Path) -> str:
    """Best-effort lookup of ``documenter.default_mode`` in the project config.

    Returns ``"auto"`` when the config file is missing or unreadable —
    the TUI never crashes on a config issue.
    """
    try:  # imports are local so the TUI module stays cheap to import
        from cortex.workspace.layout import WorkspaceLayout
    except Exception:  # noqa: BLE001
        return "auto"
    try:
        layout = WorkspaceLayout.discover(project_root)
        config_path = layout.repo_root / ".cortex" / "config.yaml"
        if not config_path.is_file():
            return "auto"
        import yaml  # local import — already a project dep

        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        documenter = data.get("documenter") or {}
        return str(documenter.get("default_mode", "auto"))
    except Exception:  # noqa: BLE001
        return "auto"


def run_tui(
    service: SessionService,
    *,
    project_root: Path,
    refresh_interval: float = 1.5,
    console: Console | None = None,
    focus_session_id: str | None = None,
) -> None:
    """Run the live TUI loop until the user presses Ctrl+C.

    The loop:
        1. Build initial state, render once.
        2. Sleep ``refresh_interval``.
        3. Cheap mtime check — if anything changed, re-build state.
        4. Re-render (always; updates "X ago" timers cheaply).
        5. On ``KeyboardInterrupt``: print a tidy goodbye, exit 0.
    """
    console = console or Console()

    if not console.is_terminal:
        # Piped or redirected output: a TUI doesn't make sense.
        console.print(
            "[red]✗[/red] `cortex session watch` requires an interactive terminal. "
            "Use `cortex session show` for one-shot output."
        )
        raise typer.Exit(1)

    documenter_mode = _resolve_documenter_mode(project_root)

    prev_active_mtime = _safe_mtime(service.active_pointer_path())
    prev_session_mtimes = _snapshot_session_mtimes(service)

    state = _build_state(
        service,
        project_root=project_root,
        focus_session_id=focus_session_id,
        refresh_tick=0,
        refresh_interval=refresh_interval,
        documenter_mode=documenter_mode,
    )

    # Quiet the project logger during the live loop — log lines smear
    # the TUI. We restore the previous handlers on exit.
    root_logger = logging.getLogger()
    previous_handlers = list(root_logger.handlers)
    root_logger.handlers = [logging.NullHandler()]

    try:
        with Live(
            render_layout(state, max_width=console.width, console=console),
            console=console,
            refresh_per_second=4,
            screen=False,
        ) as live:
            tick = 0
            while True:
                time.sleep(refresh_interval)
                tick += 1
                changed, prev_active_mtime, prev_session_mtimes = _detect_changes(
                    service,
                    prev_active_mtime=prev_active_mtime,
                    prev_session_mtimes=prev_session_mtimes,
                )
                if changed or tick % _SIDEBAR_REFRESH_EVERY == 0:
                    state = _build_state(
                        service,
                        project_root=project_root,
                        focus_session_id=focus_session_id,
                        refresh_tick=tick,
                        refresh_interval=refresh_interval,
                        documenter_mode=documenter_mode,
                        previous_recent=state.recent_sessions,
                    )
                # Always re-render — updates "X ago" timestamps and the
                # "refreshed: HH:MM:SS" indicator in the header.
                live.update(render_layout(state, max_width=console.width, console=console))
    except KeyboardInterrupt:
        console.print(
            "\n[dim]" + (glyph("check", console=console) or "OK") +
            " Session watch stopped. Session is still OPEN.[/dim]"
        )
        raise typer.Exit(0) from None
    finally:
        root_logger.handlers = previous_handlers


__all__ = [
    "SessionTuiState",
    "render_layout",
    "run_tui",
]
