"""
cortex.pipeline.stages.test
-----------------------------
TestStage — test suite execution and coverage enforcement gate.

Runs pytest (Python) or the project's test script (Node/other) and
enforces a minimum coverage threshold. Blocks the pipeline if tests
fail or coverage is below the configured minimum.
"""

from __future__ import annotations

import logging
import re
import subprocess
import time

from cortex.pipeline.domain.context import PipelineContext
from cortex.pipeline.domain.types import StageResult, StageStatus, StageType

logger = logging.getLogger(__name__)


class TestStage:
    """
    Test suite execution and coverage enforcement stage.

    Runs the test command and optionally enforces a minimum coverage
    percentage. For Python projects, uses pytest with coverage reporting.

    Args:
        command:          Override the auto-detected test command.
        min_coverage:     Minimum coverage % required to pass (0 = disabled).
        block_on_failure: If True, pipeline aborts on test failure.
        timeout_s:        Maximum seconds to wait for tests.
    """

    def __init__(
        self,
        command: str | None = None,
        min_coverage: int = 0,
        block_on_failure: bool = True,
        timeout_s: int = 300,
    ) -> None:
        self._command = command
        self._min_coverage = min_coverage
        self._block = block_on_failure
        self._timeout_s = timeout_s

    @property
    def name(self) -> str:
        return "Tests"

    @property
    def stage_type(self) -> StageType:
        return StageType.TEST

    @property
    def block_on_failure(self) -> bool:
        return self._block

    def execute(self, ctx: PipelineContext) -> StageResult:
        """Run the test suite and check coverage."""
        start = time.monotonic()
        cmd = self._command or self._detect_command(ctx)

        if not cmd:
            return StageResult(
                stage_type=self.stage_type,
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                message="No test command detected for this project type.",
                duration_ms=0,
            )

        try:
            logger.info("Running tests: %s", cmd)
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=self._timeout_s,
            )
            duration_ms = int((time.monotonic() - start) * 1000)

            # Extract coverage percentage from pytest output if available
            coverage = self._extract_coverage(result.stdout)

            if result.returncode != 0:
                # Count failures from pytest summary line
                fail_match = re.search(r"(\d+) failed", result.stdout)
                fail_count = int(fail_match.group(1)) if fail_match else "unknown"
                return StageResult(
                    stage_type=self.stage_type,
                    stage_name=self.name,
                    status=StageStatus.FAILED,
                    message=f"{fail_count} test(s) failed.",
                    artifacts={
                        "command": cmd,
                        "output": result.stdout[-3000:],  # tail of output
                        "coverage_pct": coverage,
                    },
                    duration_ms=duration_ms,
                )

            # Tests passed — now check coverage threshold
            if self._min_coverage > 0 and coverage is not None:
                if coverage < self._min_coverage:
                    return StageResult(
                        stage_type=self.stage_type,
                        stage_name=self.name,
                        status=StageStatus.FAILED,
                        message=(
                            f"Coverage {coverage:.1f}% is below minimum "
                            f"{self._min_coverage}%."
                        ),
                        artifacts={
                            "command": cmd,
                            "coverage_pct": coverage,
                            "min_coverage": self._min_coverage,
                        },
                        duration_ms=duration_ms,
                    )

            # Parse pass count for the summary message
            pass_match = re.search(r"(\d+) passed", result.stdout)
            pass_count = int(pass_match.group(1)) if pass_match else "all"
            coverage_msg = f", coverage: {coverage:.1f}%" if coverage else ""

            return StageResult(
                stage_type=self.stage_type,
                stage_name=self.name,
                status=StageStatus.PASSED,
                message=f"{pass_count} tests passed{coverage_msg}.",
                artifacts={
                    "command": cmd,
                    "coverage_pct": coverage,
                    "passed_count": pass_count,
                },
                duration_ms=duration_ms,
            )

        except subprocess.TimeoutExpired:
            duration_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_type=self.stage_type,
                stage_name=self.name,
                status=StageStatus.ERROR,
                message=f"Tests timed out after {self._timeout_s}s.",
                duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.exception("TestStage raised an unexpected error")
            return StageResult(
                stage_type=self.stage_type,
                stage_name=self.name,
                status=StageStatus.ERROR,
                message=f"Unexpected error: {exc}",
                artifacts={"error": str(exc)},
                duration_ms=duration_ms,
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_command(ctx: PipelineContext) -> str | None:
        """Detect the test command from changed file extensions."""
        extensions = {
            f.rsplit(".", 1)[-1].lower()
            for f in ctx.changed_files
            if "." in f
        }
        if "py" in extensions:
            return "pytest --cov=. --cov-report=term-missing -q"
        if "ts" in extensions or "js" in extensions:
            return "npm test"
        if "go" in extensions:
            return "go test ./..."
        if "rs" in extensions:
            return "cargo test"
        return None

    @staticmethod
    def _extract_coverage(output: str) -> float | None:
        """
        Extract the overall coverage percentage from pytest --cov output.

        Example line: ``TOTAL   1234   200   84%``
        """
        match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
        if match:
            return float(match.group(1))
        # Fallback: look for "X% coverage"
        match = re.search(r"(\d+(?:\.\d+)?)\s*%\s+coverage", output)
        if match:
            return float(match.group(1))
        return None
