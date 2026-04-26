"""
cortex.services.spec_service
-----------------------------
Domain service for creating and persisting implementation specifications.

Extracted from ``AgentMemory`` to satisfy the Single Responsibility
Principle. This service owns the entire lifecycle of a Specification:
validation, vault persistence, selective indexing, and episodic storage.

Depends on:
- ``cortex.documentation.write_spec_note``  (persistence)
- ``cortex.semantic.vault_reader.VaultReader``   (semantic indexing)
- ``cortex.episodic.memory_store.EpisodicMemoryStore`` (episodic memory)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from cortex.documentation import write_spec_note
from cortex.models import MemoryEntry

if TYPE_CHECKING:
    from cortex.episodic.memory_store import EpisodicMemoryStore
    from cortex.semantic.vault_reader import VaultReader

logger = logging.getLogger(__name__)


class SpecService:
    """
    Creates and persists implementation specifications.

    Responsibilities:
    - Write a structured spec note to the vault (``vault/specs/``).
    - Selectively index ONLY the new spec in the semantic vector store
      (avoids expensive full re-sync).
    - Optionally create an episodic memory entry for retrieval by future
      agents working on related tasks.

    Args:
        vault_path: Absolute or relative path to the Obsidian vault.
        semantic:   VaultReader instance for semantic indexing.
        episodic:   EpisodicMemoryStore instance for episodic memory.
    """

    def __init__(
        self,
        vault_path: str | Path,
        semantic: VaultReader,
        episodic: EpisodicMemoryStore,
        context_metadata: dict[str, str] | None = None,
    ) -> None:
        self._vault_path = Path(vault_path)
        self._semantic = semantic
        self._episodic = episodic
        self._context_metadata = dict(context_metadata or {})

    def create(
        self,
        *,
        title: str,
        goal: str,
        requirements: list[str] | None = None,
        files_in_scope: list[str] | None = None,
        constraints: list[str] | None = None,
        acceptance_criteria: list[str] | None = None,
        tags: list[str] | None = None,
        sync_vault: bool = False,
        remember: bool = True,
    ) -> Path:
        """
        Create a specification note and persist it to the vault.

        Follows the v2.22 selective-indexing architecture: only the
        newly created spec is vectorised, not the entire vault.

        Args:
            title:               Human-readable specification title.
            goal:                What this spec aims to achieve.
            requirements:        Functional requirements list.
            files_in_scope:      Files affected by this specification.
            constraints:         Technical or business constraints.
            acceptance_criteria: Definition of Done items.
            tags:                Vault front-matter tags.
            sync_vault:          If True, also re-index the full vault.
            remember:            If True, store a summary in episodic memory.

        Returns:
            Path to the newly created spec note file.
        """
        path = write_spec_note(
            self._vault_path,
            title=title,
            goal=goal,
            requirements=requirements or [],
            files_in_scope=files_in_scope or [],
            constraints=constraints or [],
            acceptance_criteria=acceptance_criteria or [],
            tags=tags or [],
        )
        logger.debug("Spec note written: %s", path)

        # SELECTIVE INDEXING — vectorise only this new spec
        rel_path = str(path.relative_to(self._vault_path))
        self._semantic.index_file(rel_path)

        if sync_vault:
            self._semantic.sync()

        if remember:
            self._store_episodic(
                title=title,
                goal=goal,
                requirements=requirements or [],
                files_in_scope=files_in_scope or [],
                tags=tags or [],
            )

        return path

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _store_episodic(
        self,
        *,
        title: str,
        goal: str,
        requirements: list[str],
        files_in_scope: list[str],
        tags: list[str],
    ) -> MemoryEntry:
        """Store a compact spec summary in episodic memory."""
        summary_parts = [f"Specification: {title}", f"Goal: {goal}"]
        if requirements:
            summary_parts.append("Requirements: " + "; ".join(requirements[:8]))

        return self._episodic.add(
            content="\n".join(summary_parts),
            memory_type="spec",
            tags=["spec"] + list(tags),
            files=files_in_scope,
            extra_metadata=dict(self._context_metadata),
        )
