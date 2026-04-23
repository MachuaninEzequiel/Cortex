"""
cortex.pipeline.stages.documentation
--------------------------------------
DocumentationStage — doc verification and fallback generation gate.

This is the stage that enforces the DevSecDocOps "done protocol":
work is not done until it is documented.

Flow:
1. Use ``doc_verifier`` to check if agent-written docs exist for this PR.
2. If YES  → index them into the semantic memory. PASS.
3. If NO   → generate a fallback session note. WARN (not block by default).

The stage integrates with ``AgentMemory`` to store the PR context as
an episodic memory regardless of whether docs were found.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from cortex.pipeline.domain.context import PipelineContext
from cortex.pipeline.domain.types import StageResult, StageStatus, StageType

if TYPE_CHECKING:
    from cortex.core import AgentMemory
    from cortex.models import PRContext

logger = logging.getLogger(__name__)


class DocumentationStage:
    """
    Documentation verification and fallback generation stage.

    Checks whether the PR contains agent-written documentation in the
    vault. If not, auto-generates a fallback session note so the work
    is never lost.

    Args:
        memory:           AgentMemory instance for storage and indexing.
        block_on_failure: If True, missing docs blocks the pipeline.
                          Default is False (docs are encouraged, not forced).
        pr_ctx:           Optional PRContext for doc generation / storage.
    """

    def __init__(
        self,
        memory: AgentMemory,
        block_on_failure: bool = False,
        pr_ctx: PRContext | None = None,
    ) -> None:
        self._memory = memory
        self._block = block_on_failure
        self._pr_ctx = pr_ctx

    @property
    def name(self) -> str:
        return "Documentation"

    @property
    def stage_type(self) -> StageType:
        return StageType.DOCUMENTATION

    @property
    def block_on_failure(self) -> bool:
        return self._block

    def execute(self, ctx: PipelineContext) -> StageResult:
        """
        Verify documentation and generate fallback if needed.

        Also stores the PR context (with pipeline results from previous
        stages) into episodic memory for future retrieval.
        """
        start = time.monotonic()

        try:
            # Step 1: Store PR context with results from previous stages
            if self._pr_ctx is not None:
                self._store_pr_with_results(ctx)

            # Step 2: Verify if agent-written docs exist
            has_docs = self._verify_docs(ctx)

            duration_ms = int((time.monotonic() - start) * 1000)

            if has_docs:
                # Index the agent-written docs into semantic memory
                doc_count = self._index_docs(ctx)
                return StageResult(
                    stage_type=self.stage_type,
                    stage_name=self.name,
                    status=StageStatus.PASSED,
                    message=f"Agent documentation found and indexed ({doc_count} docs).",
                    artifacts={"has_agent_docs": True, "indexed": doc_count},
                    duration_ms=duration_ms,
                )
            else:
                # Generate fallback documentation
                fallback_path = self._generate_fallback(ctx)
                return StageResult(
                    stage_type=self.stage_type,
                    stage_name=self.name,
                    status=StageStatus.FAILED if self._block else StageStatus.PASSED,
                    message=(
                        f"No agent docs found. Fallback generated: {fallback_path}"
                        if fallback_path
                        else "No agent docs found. Fallback generation skipped."
                    ),
                    artifacts={
                        "has_agent_docs": False,
                        "fallback_path": str(fallback_path) if fallback_path else None,
                    },
                    duration_ms=duration_ms,
                )

        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.exception("DocumentationStage raised an unexpected error")
            return StageResult(
                stage_type=self.stage_type,
                stage_name=self.name,
                status=StageStatus.ERROR,
                message=f"Documentation stage error: {exc}",
                artifacts={"error": str(exc)},
                duration_ms=duration_ms,
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _store_pr_with_results(self, ctx: PipelineContext) -> None:
        """Store PR context enriched with results from previous stages."""
        if self._pr_ctx is None:
            return

        # Pull results stored by previous stages
        lint_result   = ctx.get_stage_output("Lint",  "status", None)
        test_result   = ctx.get_stage_output("Tests", "status", None)
        audit_result  = ctx.get_stage_output("Security Audit", "status", None)

        try:
            self._memory.store_pr_context(
                self._pr_ctx,
                lint_result=str(lint_result) if lint_result else None,
                audit_result=str(audit_result) if audit_result else None,
                test_result=str(test_result) if test_result else None,
            )
            logger.debug("PR context stored in episodic memory")
        except Exception as exc:
            logger.warning("Could not store PR context: %s", exc)

    def _verify_docs(self, ctx: PipelineContext) -> bool:
        """Check whether agent-written docs exist for the current PR."""
        try:
            from cortex.doc_verifier import DocVerifier
            verifier = DocVerifier(vault_path=str(ctx.vault_path))
            status = verifier.verify_from_list(changed_files=self._pr_ctx.files_changed if self._pr_ctx else [])
            return bool(status and getattr(status, "has_agent_docs", False))
        except Exception as exc:
            logger.debug("Doc verification failed (non-blocking): %s", exc)
            # Fall back to simple file check
            sessions_dir = ctx.vault_path / "sessions"
            return sessions_dir.exists() and any(sessions_dir.iterdir())

    def _index_docs(self, ctx: PipelineContext) -> int:
        """Index agent-written docs into semantic memory."""
        try:
            return self._memory.sync_vault()
        except Exception as exc:
            logger.warning("Vault sync failed: %s", exc)
            return 0

    def _generate_fallback(self, ctx: PipelineContext) -> str | None:
        """Generate a fallback session note when no agent docs exist."""
        if self._pr_ctx is None:
            return None
        try:
            docs = self._memory.generate_pr_docs(self._pr_ctx)
            written = self._memory.write_pr_docs(docs)
            return written[0] if written else None
        except Exception as exc:
            logger.warning("Fallback doc generation failed: %s", exc)
            return None
