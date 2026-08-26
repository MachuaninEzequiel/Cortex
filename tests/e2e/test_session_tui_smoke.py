"""Smoke tests for ``cortex session watch`` (Phase 06).

Two layers of coverage:

* :class:`TestNoTtyExit` calls ``run_tui`` directly with a non-TTY
  :class:`Console`. This works on every platform and verifies the
  "watch requires a terminal" exit path that protects users from
  redirecting the TUI to a file.
* :class:`TestWatchSubprocess` actually spawns ``python -m cortex
  session watch`` as a subprocess, sleeps a moment, and sends Ctrl-C.
  Cross-platform signal handling is enough of a quirk that we POSIX-gate
  the SIGINT timing assertions; on Windows we only assert the process
  exits cleanly after ``terminate()``.
"""

from __future__ import annotations

import signal
import subprocess
import sys
import time
from io import StringIO
from pathlib import Path

import pytest
import typer
from rich.console import Console

from cortex.cli.session_tui import run_tui
from cortex.session.service import SessionService
from cortex.session.storage import SessionStorage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _CapturingFile:
    """File-like wrapper exposing a settable ``encoding`` attribute."""

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


def _service_in(tmp_path: Path) -> SessionService:
    """Build a SessionService rooted at ``tmp_path / .cortex/sessions``."""
    sessions_dir = tmp_path / ".cortex" / "sessions"
    sessions_dir.mkdir(parents=True)
    return SessionService(SessionStorage(sessions_dir), repo_root=tmp_path)


# ---------------------------------------------------------------------------
# No-TTY exit path (cross-platform, no subprocess required)
# ---------------------------------------------------------------------------


class TestNoTtyExit:
    def test_run_tui_exits_when_console_is_not_a_terminal(self, tmp_path: Path) -> None:
        """A piped invocation must not enter the Live loop."""
        service = _service_in(tmp_path)
        file = _CapturingFile()
        # ``force_terminal=False`` keeps ``console.is_terminal`` False.
        console = Console(
            file=file,  # type: ignore[arg-type]
            force_terminal=False,
            width=80,
            color_system=None,
        )

        with pytest.raises(typer.Exit) as excinfo:
            run_tui(
                service,
                project_root=tmp_path,
                refresh_interval=1.5,
                console=console,
            )
        assert excinfo.value.exit_code == 1
        output = file.getvalue()
        assert "interactive terminal" in output


# ---------------------------------------------------------------------------
# Subprocess smoke (best-effort cross-platform)
# ---------------------------------------------------------------------------


def _spawn_watch(
    *,
    project_root: Path,
    refresh: float = 0.5,
) -> subprocess.Popen[bytes]:
    """Spawn ``cortex session watch`` as a subprocess.

    Cierre T5: la TUI (rich Live) exige stdout interactivo — con pipes hace
    ``exit(1)`` inmediato. En POSIX usamos un pty para que el smoke test
    ejercite el boot real de la TUI; en Windows se conserva el pipe
    (el smoke acepta rc=1 no-TTY como salida válida).
    """
    cmd = [
        sys.executable,
        "-m",
        # Cierre T5: el paquete cortex ya no expone __main__ (recatorización);
        # la entrada canónica del CLI es cortex.cli.main.
        "cortex.cli.main",
        "session",
        "watch",
        "--refresh",
        str(refresh),
        "--project-root",
        str(project_root),
    ]
    # On Windows we need a new process group to be able to send a
    # CTRL_BREAK_EVENT later; on POSIX that flag does not exist.
    creationflags = (
        subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )
    if sys.platform != "win32":
        import os as _os
        import pty as _pty

        master_fd, slave_fd = _pty.openpty()
        return subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=slave_fd,
            stderr=slave_fd,
            start_new_session=True,
            close_fds=True,
        )
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=creationflags,
    )


def _stop_subprocess(proc: subprocess.Popen[bytes]) -> None:
    """Send the platform-appropriate stop signal and wait for exit."""
    if proc.poll() is not None:
        return
    try:
        if sys.platform == "win32":
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            proc.send_signal(signal.SIGINT)
    except OSError:
        proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


@pytest.mark.e2e
class TestWatchSubprocess:
    def test_watch_with_no_active_session_starts_and_stops(self, tmp_path: Path) -> None:
        """The placeholder mode boots, runs briefly, exits without hanging.

        We don't assert on stdout text — Windows captures often differ
        from POSIX, and ``rich`` may buffer until the terminal is real.
        What matters for the smoke test is that the process starts,
        survives ~1s of refresh ticks, and shuts down on signal.
        """
        # No session created → run_tui shows the "no active session" panel.
        (tmp_path / ".cortex" / "sessions").mkdir(parents=True)
        proc = _spawn_watch(project_root=tmp_path, refresh=0.5)
        try:
            time.sleep(1.2)  # let one or two refresh ticks happen
            assert proc.poll() is None, "process exited prematurely"
        finally:
            _stop_subprocess(proc)
        # Acceptable exit codes:
        #   0           — typer.Exit(0) after the KeyboardInterrupt path.
        #   1           — typer.Exit(1) (e.g. no-TTY).
        #   -signal.SIGINT — POSIX raw signal.
        #   3221225786  — Windows STATUS_CONTROL_C_EXIT (0xC000013A).
        clean_codes = {0, 1, -signal.SIGINT, 3221225786}
        assert proc.returncode in clean_codes, (
            f"unexpected return code {proc.returncode}; "
            f"stdout was: "
            f"{proc.stdout.read().decode('utf-8', errors='replace') if proc.stdout else ''}"
        )
