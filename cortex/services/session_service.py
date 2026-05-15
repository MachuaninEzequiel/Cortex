"""
cortex.services.session_service
--------------------------------
Domain service for creating and persisting session notes.

Extracted from ``AgentMemory`` to satisfy the Single Responsibility
Principle. This service owns the complete lifecycle of a Session Note:
vault persistence, selective indexing, and episodic memory storage.

Depends on:
- ``cortex.documentation.write_session_note_canonical`` (persistence)
- ``cortex.semantic.vault_reader.VaultReader``     (semantic indexing)
- ``cortex.episodic.memory_store.EpisodicMemoryStore`` (episodic memory)
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from cortex.documentation import write_session_note_canonical
from cortex.documentation.data import SessionData
from cortex.documentation.writers import VaultLike
from cortex.models import MemoryEntry

if TYPE_CHECKING:
    from cortex.episodic.memory_store import EpisodicMemoryStore
    from cortex.semantic.vault_reader import VaultReader


class _PathOnlyVault:
    """Minimal VaultLike that wraps a bare path for canonical writers.

    SessionService receives ``vault_path`` directly (not a VaultReader) for
    persistence. Indexing happens separately through ``self._semantic``.
    """

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def path(self) -> Path:
        return self._root

    def index_file(self, relative_path: str) -> bool:
        return False

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
        handoff: bool = False,
        blockers: list[str] | None = None,
        verified_state: list[str] | None = None,
        unverified_claims: list[str] | None = None,
        suggested_skills: list[str] | None = None,
        cortex_telemetry: dict | None = None,
    ) -> Path:
        """
        Create a session note and persist it to the vault.

        Follows the v2.22 selective-indexing architecture: only the
        newly created session note is vectorised, not the entire vault.

        Args:
            title:             Session title (e.g. "Fix login refresh bug").
            spec_summary:      The specification that was implemented.
            changes_made:      List of changes performed.
            files_touched:     Files modified during the session.
            key_decisions:     Architectural or design decisions taken.
            next_steps:        Remaining work items.
            tags:              Vault front-matter tags.
            sync_vault:        If True, also re-index the full vault after saving.
            remember:          If True, store a summary in episodic memory.
            handoff:           If True, mark the note as a cross-session handoff
                               (status: handoff, ``handoff`` tag added).
            blockers:          Open blockers the next agent must resolve.
            verified_state:    Facts cross-checked against diff/tests.
            unverified_claims: Statements the next agent should re-check.
            suggested_skills:  Skills/subagents recommended to continue.

        Returns:
            Path to the newly created session note file.
        """
        final_tags = ["session"] + list(tags or [])
        if handoff and "handoff" not in final_tags:
            final_tags.append("handoff")
        status = "handoff" if handoff else "completed"

        data = SessionData(
            title=title,
            tags=final_tags,
            status=status,
            session_id=uuid.uuid4().hex[:12],
            spec_summary=spec_summary or "",
            changes_made=list(changes_made or []),
            files_touched=list(files_touched or []),
            key_decisions=list(key_decisions or []),
            next_steps=list(next_steps or []),
            verified_state=list(verified_state or []),
            unverified_claims=list(unverified_claims or []),
            blockers=list(blockers or []),
            suggested_skills=list(suggested_skills or []),
            cortex_telemetry=cortex_telemetry,
        )
        vault: VaultLike = _PathOnlyVault(self._vault_path)
        path = write_session_note_canonical(data, vault=vault)
        logger.debug("Session note written: %s", path)

        # SELECTIVE INDEXING — vectorise only this new session note
        rel_path = str(path.relative_to(self._vault_path))
        self._semantic.index_file(rel_path)

        if sync_vault:
            self._semantic.sync()

        if remember:
            episodic_tags = list(tags or [])
            if handoff and "handoff" not in episodic_tags:
                episodic_tags.append("handoff")
            self._store_episodic(
                title=title,
                spec_summary=spec_summary,
                changes_made=changes_made or [],
                files_touched=files_touched or [],
                key_decisions=key_decisions or [],
                tags=episodic_tags,
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
