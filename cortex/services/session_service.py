"""
cortex.services.session_service
--------------------------------
Domain service for creating and persisting session notes.

Extracted from ``AgentMemory`` to satisfy the Single Responsibility
Principle. This service owns the complete lifecycle of a Session Note:
vault persistence, selective indexing, and episodic memory storage.

Depends on:
- ``cortex.documentation.write_session_note`` (persistence)
- ``cortex.semantic.vault_reader.VaultReader``     (semantic indexing)
- ``cortex.episodic.memory_store.EpisodicMemoryStore`` (episodic memory)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from cortex.documentation import write_session_note
from cortex.models import MemoryEntry

if TYPE_CHECKING:
    from cortex.episodic.memory_store import EpisodicMemoryStore
    from cortex.semantic.vault_reader import VaultReader

logger = logging.getLogger(__name__)


class SessionService:
    """
    Creates and persists session notes documenting completed work.

    Responsibilities:
    - Write a structured session note to the vault (``vault/sessions/``).
    - Selectively index ONLY the new note in the semantic vector store.
    - Optionally create an episodic memory entry for future context retrieval.

    This is the service that agents call at the end of a working session
    to satisfy the "done protocol": work is not done until it is documented.

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
        spec_summary: str,
        changes_made: list[str] | None = None,
        files_touched: list[str] | None = None,
        key_decisions: list[str] | None = None,
        next_steps: list[str] | None = None,
        tags: list[str] | None = None,
        sync_vault: bool = False,
        remember: bool = True,
    ) -> Path:
        """
        Create a session note and persist it to the vault.

        Follows the v2.22 selective-indexing architecture: only the
        newly created session note is vectorised, not the entire vault.

        Args:
            title:         Session title (e.g. "Fix login refresh bug").
            spec_summary:  The specification that was implemented.
            changes_made:  List of changes performed.
            files_touched: Files modified during the session.
            key_decisions: Architectural or design decisions taken.
            next_steps:    Remaining work items.
            tags:          Vault front-matter tags.
            sync_vault:    If True, also re-index the full vault after saving.
            remember:      If True, store a summary in episodic memory.

        Returns:
            Path to the newly created session note file.
        """
        path = write_session_note(
            self._vault_path,
            title=title,
            spec_summary=spec_summary,
            changes_made=changes_made or [],
            files_touched=files_touched or [],
            key_decisions=key_decisions or [],
            next_steps=next_steps or [],
            tags=tags or [],
        )
        logger.debug("Session note written: %s", path)

        # SELECTIVE INDEXING — vectorise only this new session note
        rel_path = str(path.relative_to(self._vault_path))
        self._semantic.index_file(rel_path)

        if sync_vault:
            self._semantic.sync()

        if remember:
            self._store_episodic(
                title=title,
                spec_summary=spec_summary,
                changes_made=changes_made or [],
                files_touched=files_touched or [],
                key_decisions=key_decisions or [],
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
        spec_summary: str,
        changes_made: list[str],
        files_touched: list[str],
        key_decisions: list[str],
        tags: list[str],
    ) -> MemoryEntry:
        """Store a compact session summary in episodic memory."""
        summary_parts = [
            f"Session: {title}",
            f"Specification: {spec_summary}",
        ]
        if changes_made:
            summary_parts.append("Changes: " + "; ".join(changes_made[:8]))
        if key_decisions:
            summary_parts.append("Decisions: " + "; ".join(key_decisions[:5]))

        return self._episodic.add(
            content="\n".join(summary_parts),
            memory_type="session",
            tags=["session"] + list(tags),
            files=files_touched,
            extra_metadata=dict(self._context_metadata),
        )
