"""
cortex.pipeline.orchestrator
-----------------------------
PipelineOrchestrator — executes stages in order, enforces gates.

The orchestrator is the single coordination point for a pipeline run.
It knows about:
- Which stages to run (injected as a list)
- Whether to abort when a blocking stage fails (gate enforcement)
- How to collect and aggregate results into a PipelineReport

It does NOT know about:
- CI providers (that's the runners' job)
- Business logic of individual stages (that's each stage's job)
- How results are displayed (that's the report's job)
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from cortex.pipeline.domain.context import PipelineContext
from cortex.pipeline.domain.protocols import PipelineStage
from cortex.pipeline.domain.types import PipelineReport, StageResult, StageStatus

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Executes a sequence of pipeline stages and returns a PipelineReport.

    Stages are run in the order they are provided. If a blocking stage
    fails (``stage.block_on_failure == True``), the orchestrator stops
    and marks all remaining stages as SKIPPED.

    Args:
        stages:      Ordered list of stages to execute.
        abort_early: If False, run ALL stages regardless of failures.
                     Useful for collecting complete diagnostics.
    """

    def __init__(
        self,
        stages: list[PipelineStage],
        abort_early: bool = True,
    ) -> None:
        self._stages = stages
        self._abort_early = abort_early

    def run(self, ctx: PipelineContext) -> PipelineReport:
        """
        Execute all stages and return a consolidated PipelineReport.

        For each stage:
        1. Call ``stage.execute(ctx)``.
        2. Store the stage's status in ``ctx.stage_outputs`` for
           downstream stages to read.
        3. If the stage failed and ``block_on_failure`` is True,
           abort and skip remaining stages.

        Args:
            ctx: Shared pipeline context.

        Returns:
            PipelineReport with all results.
        """
        started_at = datetime.now(timezone.utc)
        results: list[StageResult] = []
        aborted = False

        for stage in self._stages:
            if aborted:
                # Mark remaining stages as skipped
                results.append(StageResult(
                    stage_type=stage.stage_type,
                    stage_name=stage.name,
                    status=StageStatus.SKIPPED,
                    message="Skipped due to earlier gate failure.",
                ))
                continue

            logger.info("▶  Running stage: %s", stage.name)
            stage_start = time.monotonic()

            result = stage.execute(ctx)
            results.append(result)

            # Propagate status to ctx so downstream stages can read it
            ctx.set_stage_output(stage.name, "status", result.status.value)
            ctx.set_stage_output(stage.name, "passed", result.passed)
            ctx.set_stage_output(stage.name, "artifacts", result.artifacts)

            logger.info(
                "%s  Stage %s: %s in %dms",
                result.icon,
                stage.name,
                result.status.value,
                result.duration_ms,
            )

            # Gate enforcement
            if result.failed and stage.block_on_failure and self._abort_early:
                logger.warning(
                    "🚨 Gate failed: %s. Aborting pipeline.", stage.name
                )
                aborted = True

        ended_at = datetime.now(timezone.utc)
        report = PipelineReport(
            results=results,
            started_at=started_at,
            ended_at=ended_at,
        )
        logger.info(report.summary())
        return report
