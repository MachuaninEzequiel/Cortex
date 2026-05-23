"""Tests for :mod:`cortex.cli.session_tui` — pure render functions.

The :func:`render_layout` function is a pure mapping from
:class:`SessionTuiState` to ``rich.layout.Layout``. All these tests
print into a ``StringIO``-backed ``Console`` and assert on the captured
text — never touch a real TTY and never invoke ``run_tui``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path

from rich.console import Console

from cortex.cli.session_tui import (
    SessionTuiState,
    _format_duration_ms,
    _format_relative,
    render_layout,
)
from cortex.session.models import (
    Checkpoint,
    CheckpointSource,
    SessionMode,
    SessionRecord,
    SessionStatus,
    VerificationHookResult,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _CapturingFile:
    """File-like wrapper with a settable ``encoding`` attribute (StringIO's
    is read-only). Used by all tests that need to inspect rendered output."""

    def __init__(self, encoding: str = "utf-8") -> None:
        self._buffer = StringIO()
        self.encoding = encoding

    def write(self, value: str) -> int:
        return self._buffer.write(value)

    def flush(self) -> None:
        return None

    def isatty(self) -> bool:
        return False

    def getvalue(self) -> str:
        return self._buffer.getvalue()


def _console(
    width: int = 200,
    encoding: str = "utf-8",
    height: int = 60,
) -> Console:
    """A force-terminal Console that writes to a capturing buffer.

    Layout rendering needs a fixed height; without it, rich queries the
    real terminal (and inside pytest may collapse to 0 rows for some
    panels). We pin both dimensions explicitly for predictable output.
    """
    return Console(
        file=_CapturingFile(encoding),  # type: ignore[arg-type]
        force_terminal=True,
        width=width,
        height=height,
        color_system=None,
    )


def _render_to_text(
    state: SessionTuiState,
    *,
    width: int = 200,
    encoding: str = "utf-8",
    height: int = 60,
) -> str:
    console = _console(width=width, encoding=encoding, height=height)
    console.print(render_layout(state, max_width=width, console=console))
    file = console.file
    assert isinstance(file, _CapturingFile)
    return file.getvalue()


def _session(
    *,
    session_id: str = "2026-05-17_demo",
    opened_minutes_ago: int = 134,
    checkpoints: list[Checkpoint] | None = None,
    status: SessionStatus = SessionStatus.OPEN,
    mode: SessionMode = SessionMode.UNKNOWN,
    verification: list[VerificationHookResult] | None = None,
) -> SessionRecord:
    opened_at = datetime.now(UTC) - timedelta(minutes=opened_minutes_ago)
    data: dict[str, object] = {
        "session_id": session_id,
        "spec_path": Path("vault/specs/demo.md"),
        "spec_summary": "Implement the demo workflow end-to-end with tests.",
        "start_commit": "a" * 40,
        "start_branch": "feature/demo",
        "opened_at": opened_at,
        "status": status,
        "mode": mode,
        "checkpoints": checkpoints or [],
        "verification_results": verification or [],
    }
    if status is not SessionStatus.OPEN:
        data["closed_at"] = opened_at + timedelta(minutes=10)
        data["end_commit"] = "b" * 40
        data["documenter_decision"] = status
    return SessionRecord.model_validate(data)


def _checkpoint(
    *,
    source: CheckpointSource = CheckpointSource.CORTEX_SDDWORK,
    note: str = "",
    minutes_ago: int = 5,
    verified_claims: list[str] | None = None,
    artifacts: list[str] | None = None,
) -> Checkpoint:
    return Checkpoint(
        timestamp=datetime.now(UTC) - timedelta(minutes=minutes_ago),
        source=source,
        note=note,
        verified_claims=verified_claims or [],
        unverified_claims=[],
        artifacts_touched=artifacts or [],
    )


def _state(
    *,
    active: SessionRecord | None = None,
    recent: list[SessionRecord] | None = None,
    diff_preview: str = "",
    diff_error: str = "",
    branch: str = "feature/demo",
    project_name: str = "cortex",
    open_count: int = 1,
    closed_count: int = 2,
) -> SessionTuiState:
    return SessionTuiState(
        active_session=active,
        recent_sessions=recent or [],
        diff_preview=diff_preview,
        diff_error=diff_error,
        refresh_tick=0,
        repo_root=Path("/tmp/cortex"),
        project_name=project_name,
        branch=branch,
        documenter_mode="auto",
        refresh_interval=1.5,
        refreshed_at=datetime(2026, 5, 17, 14, 32, 11, tzinfo=UTC),
        total_open=open_count,
        total_closed=closed_count,
    )


# ---------------------------------------------------------------------------
# Relative-time formatter
# ---------------------------------------------------------------------------


class TestFormatRelative:
    _NOW = datetime(2026, 5, 17, 12, 0, 0, tzinfo=UTC)

    def test_just_now(self) -> None:
        ts = self._NOW - timedelta(seconds=2)
        assert _format_relative(ts, now=self._NOW) == "just now"

    def test_seconds_ago(self) -> None:
        ts = self._NOW - timedelta(seconds=30)
        assert _format_relative(ts, now=self._NOW) == "30s ago"

    def test_minutes_ago(self) -> None:
        ts = self._NOW - timedelta(minutes=12)
        assert _format_relative(ts, now=self._NOW) == "12m ago"

    def test_hours_minutes_ago(self) -> None:
        ts = self._NOW - timedelta(hours=2, minutes=14)
        assert _format_relative(ts, now=self._NOW) == "2h 14m ago"

    def test_exact_hours_no_minutes(self) -> None:
        ts = self._NOW - timedelta(hours=3)
        assert _format_relative(ts, now=self._NOW) == "3h ago"

    def test_days_hours_ago(self) -> None:
        ts = self._NOW - timedelta(days=1, hours=4)
        assert _format_relative(ts, now=self._NOW) == "1d 4h ago"

    def test_naive_input_is_assumed_utc(self) -> None:
        ts = self._NOW.replace(tzinfo=None) - timedelta(minutes=5)
        assert _format_relative(ts, now=self._NOW) == "5m ago"


class TestFormatDurationMs:
    def test_millis(self) -> None:
        assert _format_duration_ms(824) == "824ms"

    def test_seconds_decimals(self) -> None:
        assert _format_duration_ms(5_200) == "5.2s"

    def test_minutes(self) -> None:
        assert _format_duration_ms(124_000) == "2m 4s"


# ---------------------------------------------------------------------------
# Layout: no active session
# ---------------------------------------------------------------------------


class TestRenderLayoutNoSession:
    def test_shows_no_active_session_message(self) -> None:
        out = _render_to_text(_state(active=None, open_count=0, closed_count=0))
        assert "NO ACTIVE SESSION" in out
        assert "cortex create-spec" in out
        assert "Watching for a new session" in out

    def test_no_session_works_in_narrow_terminal(self) -> None:
        out = _render_to_text(_state(active=None, open_count=0), width=60)
        # The placeholder still appears in the narrow layout.
        assert "NO ACTIVE SESSION" in out


# ---------------------------------------------------------------------------
# Layout: with an active session
# ---------------------------------------------------------------------------


class TestRenderLayoutWithSession:
    def test_panels_present_at_full_width(self) -> None:
        session = _session()
        out = _render_to_text(
            _state(active=session, recent=[session]),
            width=200,
        )
        assert "ACTIVE SESSION" in out
        assert "CHECKPOINTS" in out
        assert "DIFF PREVIEW" in out
        assert "RECENT SESSIONS" in out

    def test_sidebar_hidden_at_medium_width(self) -> None:
        session = _session()
        out = _render_to_text(
            _state(active=session, recent=[session]),
            width=80,
        )
        assert "ACTIVE SESSION" in out
        assert "CHECKPOINTS" in out
        assert "RECENT SESSIONS" not in out  # dropped at medium width

    def test_stacked_at_narrow_width(self) -> None:
        session = _session()
        out = _render_to_text(
            _state(active=session, recent=[session]),
            width=60,
        )
        # Panels still render, just stacked.
        assert "ACTIVE SESSION" in out
        assert "CHECKPOINTS" in out


class TestActiveSessionPanel:
    def test_includes_session_id(self) -> None:
        session = _session(session_id="2026-05-17_jwt")
        out = _render_to_text(_state(active=session))
        assert "2026-05-17_jwt" in out

    def test_includes_relative_open_time(self) -> None:
        session = _session(opened_minutes_ago=134)
        out = _render_to_text(_state(active=session))
        assert "2h 14m ago" in out

    def test_shows_inferred_mode_marker_when_unknown(self) -> None:
        session = _session(mode=SessionMode.UNKNOWN)
        out = _render_to_text(_state(active=session))
        assert "(inferred)" in out

    def test_omits_inferred_marker_when_mode_is_set(self) -> None:
        session = _session(mode=SessionMode.MANAGED, status=SessionStatus.CLOSED)
        out = _render_to_text(_state(active=session))
        assert "(inferred)" not in out

    def test_shows_verification_pending_when_no_results(self) -> None:
        session = _session(verification=[])
        out = _render_to_text(_state(active=session))
        assert "verification not yet run" in out

    def test_shows_verification_results(self) -> None:
        verif = [
            VerificationHookResult(
                name="tests",
                command="pytest",
                passed=True,
                exit_code=0,
                output="ok",
                duration_ms=5200,
                run_at=datetime.now(UTC),
            )
        ]
        session = _session(verification=verif)
        out = _render_to_text(_state(active=session))
        assert "tests" in out
        assert "5.2s" in out


class TestCheckpointsPanel:
    def test_lists_recent_first(self) -> None:
        old = _checkpoint(source=CheckpointSource.CORTEX_SYNC, minutes_ago=30, note="old")
        new = _checkpoint(source=CheckpointSource.IDE_HOOK, minutes_ago=2, note="new")
        session = _session(checkpoints=[old, new])
        out = _render_to_text(_state(active=session))
        # Newest is closer to the top → its substring appears first.
        assert out.index("new") < out.index("old")

    def test_truncates_beyond_visible_limit(self) -> None:
        many = [_checkpoint(minutes_ago=i, note=f"cp{i}") for i in range(10)]
        session = _session(checkpoints=many)
        out = _render_to_text(_state(active=session))
        assert "earlier" in out  # the "(+ N earlier)" footer

    def test_empty_state(self) -> None:
        session = _session(checkpoints=[])
        out = _render_to_text(_state(active=session))
        assert "no checkpoints yet" in out


class TestDiffPanel:
    def test_truncates_long_diffs(self) -> None:
        diff = "\n".join(f"+line {i}" for i in range(50))
        session = _session()
        out = _render_to_text(_state(active=session, diff_preview=diff))
        assert "more lines" in out

    def test_renders_short_diff(self) -> None:
        diff = "diff --git a/x b/x\n+new\n-old"
        session = _session()
        out = _render_to_text(_state(active=session, diff_preview=diff))
        assert "+new" in out
        assert "-old" in out

    def test_empty_diff_message(self) -> None:
        session = _session()
        out = _render_to_text(_state(active=session, diff_preview=""))
        assert "no diff" in out

    def test_diff_error_surfaced(self) -> None:
        session = _session()
        out = _render_to_text(_state(active=session, diff_error="GitError"))
        assert "diff unavailable" in out
        assert "GitError" in out


class TestRecentSessionsSidebar:
    def test_active_row_marked_with_arrow(self) -> None:
        active = _session(session_id="2026-05-17_active")
        other = _session(session_id="2026-05-16_other", status=SessionStatus.CLOSED)
        out = _render_to_text(
            _state(active=active, recent=[active, other]),
            width=200,
        )
        # The arrow glyph is in the active row.
        assert "▶" in out

    def test_shows_extra_count_when_many(self) -> None:
        sessions = [
            _session(session_id=f"2026-05-{10 + i}_demo")
            for i in range(8)
        ]
        out = _render_to_text(
            _state(active=sessions[0], recent=sessions),
            width=200,
        )
        assert "more" in out  # the "(+ N more)" footer


class TestHeaderFooter:
    def test_header_includes_branch(self) -> None:
        out = _render_to_text(
            _state(active=_session(), branch="feature/jwt-refresh"),
            width=200,
        )
        assert "feature/jwt-refresh" in out

    def test_header_handles_missing_branch(self) -> None:
        out = _render_to_text(_state(active=_session(), branch=""), width=200)
        assert "<no git>" in out

    def test_footer_mentions_ctrl_c(self) -> None:
        out = _render_to_text(_state(active=_session()), width=200)
        assert "Ctrl+C" in out

    def test_footer_includes_refresh_interval(self) -> None:
        # default 1.5s
        out = _render_to_text(_state(active=_session()), width=200)
        assert "1.5s" in out
