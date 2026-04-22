"""
cortex.pipeline.stages.lint
-----------------------------
LintStage — static analysis and code style gate.

Runs the project's linter (Ruff for Python, ESLint for JS/TS, etc.)
and reports results as a typed StageResult.

The stage auto-detects the project language from the changed files
or falls back to a user-provided command.
"""

from __future__ import annotations

import logging
import subprocess
import time

from cortex.pipeline.domain.context import PipelineContext
from cortex.pipeline.domain.types import StageResult, StageStatus, StageType

logger = logging.getLogger(__name__)

# Default lint commands by language identifier
_DEFAULT_COMMANDS: dict[str, str] = {
    "python":     "ruff check .",
    "javascript": "npm run lint --if-present",
    "typescript": "npm run lint --if-present",
    "go":         "golangci-lint run",
    "rust":       "cargo clippy -- -D warnings",
}


class LintStage:
    """
    Static analysis / code style enforcement stage.

    Auto-detects the linting tool based on changed file extensions,
    or uses an explicitly provided command.

    Args:
        command:          Override the auto-detected lint command.
        block_on_failure: If True, pipeline aborts on lint errors.
        timeout_s:        Maximum seconds to wait for the linter.
    """

    def __init__(
        self,
        command: str | None = None,
        block_on_failure: bool = True,
        timeout_s: int = 120,
    ) -> None:
        self._command = command
        self._block = block_on_failure
        self._timeout_s = timeout_s

    @property
    def name(self) -> str:
        return "Lint"

    @property
    def stage_type(self) -> StageType:
        return StageType.LINT

    @property
    def block_on_failure(self) -> bool:
        return self._block

    def execute(self, ctx: PipelineContext) -> StageResult:
        """Run the lint command and parse its output."""
        start = time.monotonic()
        cmd = self._command or self._detect_command(ctx)

        if not cmd:
            return StageResult(
                stage_type=self.stage_type,
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                message="No lint command detected for this project type.",
                duration_ms=0,
            )

        try:
            logger.info("Running lint: %s", cmd)
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=self._timeout_s,
            )
            duration_ms = int((time.monotonic() - start) * 1000)

            if result.returncode == 0:
                return StageResult(
                    stage_type=self.stage_type,
                    stage_name=self.name,
                    status=StageStatus.PASSED,
                    message="No lint errors found.",
                    artifacts={"command": cmd},
                    duration_ms=duration_ms,
                )
            else:
                # Count error lines for the summary message
                error_lines = [
                    ln for ln in result.stdout.splitlines()
                    if "error" in ln.lower() or "E " in ln
                ]
                count = len(error_lines) or result.stdout.count("\n")
                return StageResult(
                    stage_type=self.stage_type,
                    stage_name=self.name,
                    status=StageStatus.FAILED,
                    message=f"{count} lint issue(s) found.",
                    artifacts={
                        "command": cmd,
                        "output": result.stdout[:2000],
                        "stderr": result.stderr[:500],
                    },
                    duration_ms=duration_ms,
                )

        except FileNotFoundError as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_type=self.stage_type,
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                message=f"Lint tool not found: {exc}",
                artifacts={"command": cmd, "error": str(exc)},
                duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.exception("LintStage raised an unexpected error")
            return StageResult(
                stage_type=self.stage_type,
                stage_name=self.name,
                status=StageStatus.ERROR,
                message=f"Unexpected error: {exc}",
                artifacts={"error": str(exc)},
                duration_ms=duration_ms,
            )

    # ------------------------------------------------------------------
    # Language detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_command(ctx: PipelineContext) -> str | None:
        """Detect the appropriate lint command from changed file extensions."""
        extensions = {
            f.rsplit(".", 1)[-1].lower()
            for f in ctx.changed_files
            if "." in f
        }
        if "py" in extensions:
            return _DEFAULT_COMMANDS["python"]
        if "ts" in extensions or "tsx" in extensions:
            return _DEFAULT_COMMANDS["typescript"]
        if "js" in extensions or "jsx" in extensions:
            return _DEFAULT_COMMANDS["javascript"]
        if "go" in extensions:
            return _DEFAULT_COMMANDS["go"]
        if "rs" in extensions:
            return _DEFAULT_COMMANDS["rust"]
        return None
