"""
cortex.services.pr_service
---------------------------
Domain service for storing PR context and generating fallback documentation.

Extracted from ``AgentMemory`` to satisfy the Single Responsibility
Principle. This service owns the DevSecDocOps PR workflow:
context enrichment, episodic storage, and fallback doc generation.

Depends on:
- ``cortex.pr_capture.enrich_with_pipeline``   (context enrichment)
- ``cortex.doc_generator.DocGenerator``         (fallback docs)
- ``cortex.episodic.memory_store.EpisodicMemoryStore`` (episodic memory)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from cortex.models import GeneratedDoc, MemoryEntry, PRContext

if TYPE_CHECKING:
    from cortex.episodic.memory_store import EpisodicMemoryStore

logger = logging.getLogger(__name__)


class PRService:
    """
    Handles the PR intake workflow in the DevSecDocOps pipeline.

    Responsibilities:
    1. Enrich a raw PRContext with pipeline results (lint, audit, tests).
    2. Store the enriched PR context as an episodic memory.
    3. Generate fallback documentation when no agent-written docs exist.
    4. Write generated docs to the vault.
    5. Search past PRs for similar context.

    Args:
        vault_path: Absolute or relative path to the Obsidian vault.
        episodic:   EpisodicMemoryStore instance for episodic memory.
    """

    def __init__(
        self,
        vault_path: str | Path,
        episodic: EpisodicMemoryStore,
        context_metadata: dict[str, str] | None = None,
    ) -> None:
        self._vault_path = Path(vault_path)
        self._episodic = episodic
        self._context_metadata = dict(context_metadata or {})

    def store_pr_context(
        self,
        ctx: PRContext,
        *,
        lint_result: str | None = None,
        audit_result: str | None = None,
        test_result: str | None = None,
    ) -> MemoryEntry:
        """
        Enrich a PRContext with pipeline results and store it as a memory.

        Args:
            ctx:          The raw PRContext captured from the PR.
            lint_result:  SAST / ESLint result string.
            audit_result: SCA / npm audit result string.
            test_result:  Test suite result string.

        Returns:
            The stored MemoryEntry with its generated ID.
        """
        from cortex.pr_capture import enrich_with_pipeline

        ctx = enrich_with_pipeline(
            ctx,
            lint_result=lint_result,
            audit_result=audit_result,
            test_result=test_result,
        )

        summary = (
            f"PR #{ctx.pr_number}: {ctx.title} by {ctx.author} "
            f"({ctx.source_branch} -> {ctx.target_branch})"
        )
        content_parts = [summary]
        if ctx.body:
            content_parts.append(f"\nDescription: {ctx.body[:500]}")
        if ctx.diff_summary:
            content_parts.append(f"\nDiff:\n{ctx.diff_summary}")
        content_parts.append(f"\nLint: {ctx.lint_result or 'n/a'}")
        content_parts.append(f"\nAudit: {ctx.audit_result or 'n/a'}")
        content_parts.append(f"\nTests: {ctx.test_result or 'n/a'}")

        return self._episodic.add(
            content="\n".join(content_parts),
            memory_type="pr",
            tags=["pr", ctx.author] + ctx.labels,
            files=ctx.files_changed[:20],
            extra_metadata=dict(self._context_metadata),
        )

    def generate_pr_docs(
        self,
        ctx: PRContext,
        *,
        skip_types: list[str] | None = None,
    ) -> list[GeneratedDoc]:
        """
        Generate fallback documentation from a PRContext.

        Used when the developer did not write docs manually during
        the session. Produces a single session note as fallback.

        Args:
            ctx:        The PR context to generate from.
            skip_types: Document types to skip (e.g. ``["session"]``).

        Returns:
            List of GeneratedDoc objects (not yet written to disk).
        """
        from cortex.doc_generator import DocGenerator

        gen = DocGenerator(vault_path=self._vault_path)
        return gen.generate_all(ctx, skip_types=skip_types or [])

    def write_pr_docs(self, docs: list[GeneratedDoc]) -> list[str]:
        """
        Write generated PR documents to the vault.

        Args:
            docs: List of GeneratedDoc to write.

        Returns:
            List of written file path strings.
        """
        from cortex.doc_generator import DocGenerator

        gen = DocGenerator(vault_path=self._vault_path)
        written = gen.write_docs(docs)
        return [str(p) for p in written]
