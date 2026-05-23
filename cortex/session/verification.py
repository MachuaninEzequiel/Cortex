"""cortex.session.verification — Run :class:`VerificationHook` commands.

The :class:`VerificationRunner` executes the hooks declared in a spec and
captures their results into :class:`VerificationHookResult` instances.
It is consumed by the documenter's reconstruction module (Phase 01 /
T1.4) but is intentionally decoupled from it — no documenter, spec
loading, vault, memory or git dependency lives here.

Design contract:

- Every hook gets a result. Hook failures (non-zero exit, timeout,
  output overflow) produce a result with ``passed=False`` and never
  raise.
- Infrastructure failures (``shell`` not found, ``OSError`` other than
  permission) bubble up as :class:`subprocess.SubprocessError` — they
  signal a broken environment and the caller decides how to surface
  them.
- ``shell=True`` is used by design: hooks come from the spec, which is
  owned by the user. If the spec is malicious the system is already
  compromised — see Phase 01 §3.5 design notes.
- The working directory is always *repo_root*; environment variables
  are inherited.
"""

from __future__ import annotations

import logging
import subprocess
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from cortex.session.models import (
    MAX_VERIFICATION_OUTPUT_BYTES,
    VerificationHook,
    VerificationHookResult,
)

logger = logging.getLogger(__name__)

# Sentinel exit code used when a hook times out. ``subprocess`` returns
# ``None`` for timed-out processes; we surface this as a stable negative
# number so callers can pattern-match without ``Optional[int]``.
_TIMEOUT_EXIT_CODE = -1


class VerificationRunner:
    """Execute :class:`VerificationHook` commands and collect results.

    Args:
        repo_root: Working directory for every hook. Must exist.
        max_output_bytes: Soft cap for the captured output. Defaults to
            :data:`cortex.session.models.MAX_VERIFICATION_OUTPUT_BYTES`.
            Override only for tests or constrained environments — the
            default already keeps a typical pytest traceback intact.
    """

    def __init__(
        self,
        repo_root: Path,
        max_output_bytes: int = MAX_VERIFICATION_OUTPUT_BYTES,
    ) -> None:
        self._repo_root = Path(repo_root)
        # The model itself truncates ``output`` to MAX_VERIFICATION_OUTPUT_BYTES
        # at validation time; keeping a separate cap here is useful when a
        # caller wants to fail fast on enormous output (avoids loading huge
        # process output into memory just to truncate it later).
        self._max_output_bytes = int(max_output_bytes)

    @property
    def repo_root(self) -> Path:
        return self._repo_root

    def run_hook(self, hook: VerificationHook) -> VerificationHookResult:
        """Execute *hook* and return its :class:`VerificationHookResult`.

        Failures (non-zero exit, timeout) never raise — they're captured
        in the returned result with ``passed=False``.
        """
        logger.info(
            "Running verification hook %s: %s (timeout=%ds)",
            hook.name,
            hook.command,
            hook.timeout_seconds,
        )
        run_at = datetime.now(UTC)
        start = time.monotonic()
        try:
            proc = subprocess.run(
                hook.command,
                shell=True,
                cwd=str(self._repo_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=hook.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            stdout = (
                exc.stdout
                if isinstance(exc.stdout, str)
                else (exc.stdout or b"").decode("utf-8", errors="replace")
            )
            stderr = (
                exc.stderr
                if isinstance(exc.stderr, str)
                else (exc.stderr or b"").decode("utf-8", errors="replace")
            )
            output = (
                self._compose_output(stdout, stderr) or f"(timeout after {hook.timeout_seconds}s)"
            )
            return VerificationHookResult(
                name=hook.name,
                command=hook.command,
                passed=False,
                exit_code=_TIMEOUT_EXIT_CODE,
                output=output,
                duration_ms=duration_ms,
                run_at=run_at,
            )

        duration_ms = int((time.monotonic() - start) * 1000)
        merged = self._compose_output(proc.stdout, proc.stderr)
        return VerificationHookResult(
            name=hook.name,
            command=hook.command,
            passed=proc.returncode == 0,
            exit_code=proc.returncode,
            output=merged,
            duration_ms=duration_ms,
            run_at=run_at,
        )

    def run_all(self, hooks: Sequence[VerificationHook]) -> list[VerificationHookResult]:
        """Run every hook sequentially in input order."""
        return [self.run_hook(h) for h in hooks]

    # ── Internals ──────────────────────────────────────────────────

    def _compose_output(self, stdout: str, stderr: str) -> str:
        """Merge stdout and stderr.

        Stderr is appended with a marker only if non-empty. We rely on
        :class:`VerificationHookResult` to truncate the merged result.
        """
        if stderr:
            return f"{stdout}\n[stderr]\n{stderr}" if stdout else stderr
        return stdout


__all__ = ["VerificationRunner"]
