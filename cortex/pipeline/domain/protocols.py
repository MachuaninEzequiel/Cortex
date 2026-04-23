"""
cortex.pipeline.domain.protocols
----------------------------------
The PipelineStage Protocol — the contract that every stage must satisfy.

Using ``typing.Protocol`` (structural subtyping) means:
1. Stages don't need to inherit from a base class.
2. Any class with the right shape satisfies the contract automatically.
3. ``runtime_checkable`` enables isinstance() validation at startup.

Gate configuration
------------------
Each stage declares whether it should block the pipeline on failure
via ``block_on_failure``. The orchestrator reads this to decide
whether to abort or continue after a failed stage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from cortex.pipeline.domain.types import StageResult, StageType

if TYPE_CHECKING:
    from cortex.pipeline.domain.context import PipelineContext


@runtime_checkable
class PipelineStage(Protocol):
    """
    Structural protocol for all DevSecDocOps pipeline stages.

    A class satisfies this protocol if it has:
    - A ``name`` property returning a str.
    - A ``stage_type`` property returning a StageType.
    - A ``block_on_failure`` property returning a bool.
    - An ``execute`` method matching the signature below.

    No inheritance is required.
    """

    @property
    def name(self) -> str:
        """Human-readable stage name (e.g. 'Run Tests')."""
        ...

    @property
    def stage_type(self) -> StageType:
        """Semantic classification used by gate rules and runners."""
        ...

    @property
    def block_on_failure(self) -> bool:
        """
        If True, the orchestrator will abort the pipeline when this
        stage fails. If False, the pipeline continues regardless.
        """
        ...

    def execute(self, ctx: PipelineContext) -> StageResult:
        """
        Run the stage logic and return an immutable result.

        Args:
            ctx: Shared pipeline context (files, PR metadata, config).
                 Stages may read ``ctx.stage_outputs`` to consume results
                 from previously executed stages.

        Returns:
            StageResult with status, message, and any artifacts.

        Note:
            Implementations MUST NOT raise exceptions. All errors should
            be caught and returned as ``StageStatus.ERROR`` results so the
            orchestrator can continue collecting results from other stages.
        """
        ...
