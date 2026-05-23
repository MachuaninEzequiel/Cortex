"""
cortex.services.spec_service
-----------------------------
Domain service for creating and persisting implementation specifications.

Extracted from ``AgentMemory`` to satisfy the Single Responsibility
Principle. This service owns the entire lifecycle of a Specification:
validation, vault persistence, selective indexing, and episodic storage.

Depends on:
- ``cortex.documentation.write_spec_note_canonical``  (persistence)
- ``cortex.semantic.vault_reader.VaultReader``   (semantic indexing)
- ``cortex.episodic.memory_store.EpisodicMemoryStore`` (episodic memory)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from cortex.documentation import write_spec_note_canonical
from cortex.documentation.data import SpecData
from cortex.documentation.writers import VaultLike
from cortex.models import MemoryEntry
from cortex.session.models import SessionRecord, VerificationHook

if TYPE_CHECKING:
    from cortex.episodic.memory_store import EpisodicMemoryStore
    from cortex.semantic.vault_reader import VaultReader
    from cortex.session.service import SessionService


@dataclass(frozen=True)
class SpecCreationResult:
    """Outcome of :meth:`SpecService.create`.

    Attributes:
        path:    Filesystem path to the persisted spec note (always set
                 on success — failures raise before returning).
        session: The :class:`SessionRecord` opened automatically alongside
                 the spec, or ``None`` when no ``SessionService`` was
                 configured on the service. Callers that need to surface
                 ``session.is_gitless`` to the user (the MCP handler does
                 this to emit a degraded-mode notice) inspect this field.
    """

    path: Path
    session: SessionRecord | None = None


class _PathOnlyVault:
    """Minimal VaultLike that wraps a bare path for canonical writers.

    SpecService receives ``vault_path`` directly (not a VaultReader) for
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
        vault_path:      Absolute or relative path to the Obsidian vault.
        semantic:        VaultReader instance for semantic indexing.
        episodic:        EpisodicMemoryStore instance for episodic memory.
        context_metadata: Project-level metadata propagated to episodic entries.
        session_service: Optional :class:`cortex.session.service.SessionService`.
            When provided, a Session is opened automatically after the spec is
            persisted. Failures opening the Session never block spec creation
            — they are logged as warnings. Introduced by the Pluggable Middle
            architecture (Phase 00 / T0.6).
    """

    def __init__(
        self,
        vault_path: str | Path,
        semantic: VaultReader,
        episodic: EpisodicMemoryStore,
        context_metadata: dict[str, str] | None = None,
        session_service: SessionService | None = None,
    ) -> None:
        self._vault_path = Path(vault_path)
        self._semantic = semantic
        self._episodic = episodic
        self._context_metadata = dict(context_metadata or {})
        self._session_service = session_service

    _VALID_PROPOSAL_MODES: frozenset[str] = frozenset({"optional", "required", "skip"})

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
        verification_hooks: list[VerificationHook] | list[dict[str, Any]] | None = None,
        sync_vault: bool = False,
        remember: bool = True,
        proposal_mode: str = "optional",
        proposal_confirmed: bool = False,
        with_tasks: bool = False,
    ) -> SpecCreationResult:
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
            verification_hooks:  Executable commands that prove the work is
                                 done (Pluggable Middle, Phase 01). Accepts
                                 :class:`VerificationHook` instances or plain
                                 dicts (auto-coerced). When empty, a warning
                                 is logged — backward-compatible read path
                                 for legacy specs created before the field
                                 existed.
            sync_vault:          If True, also re-index the full vault.
            remember:            If True, store a summary in episodic memory.
            proposal_mode:       Phase 09.A. One of ``optional`` (default —
                                 ``cortex-sync`` emits a proposal but the
                                 call may proceed without confirmation),
                                 ``required`` (the caller must set
                                 ``proposal_confirmed=True``; raises
                                 ``ValueError`` otherwise), or ``skip``
                                 (the proposal step is bypassed entirely).
            proposal_confirmed:  Phase 09.A. Set to ``True`` once the
                                 ``cortex-sync`` proposal has been
                                 acknowledged by the user. Only consulted
                                 when ``proposal_mode == "required"``.

        Returns:
            Path to the newly created spec note file.
        """
        if proposal_mode not in self._VALID_PROPOSAL_MODES:
            raise ValueError(
                f"proposal_mode must be one of "
                f"{sorted(self._VALID_PROPOSAL_MODES)}; got {proposal_mode!r}"
            )
        if proposal_mode == "required" and not proposal_confirmed:
            raise ValueError(
                "proposal_mode is 'required' but proposal was not confirmed; "
                "re-run cortex-sync to emit and confirm the proposal before "
                "creating the spec."
            )

        final_tags = ["spec"] + list(tags or [])
        if with_tasks and "tasks-required" not in final_tags:
            # Pluggable Middle Phase 09.C: signal to ``cortex-SDDwork`` that
            # this spec expects a granular task decomposition (opt-in).
            final_tags.append("tasks-required")
        hooks = self._normalize_hooks(verification_hooks)
        if not hooks:
            logger.warning(
                "Spec %r created without verification_hooks. "
                "BYO mode will skip verification on cortex finish-session.",
                title,
            )
        data = SpecData(
            title=title,
            tags=final_tags,
            status="draft",
            goal=goal or "",
            requirements=list(requirements or []),
            files_in_scope=list(files_in_scope or []),
            constraints=list(constraints or []),
            acceptance_criteria=list(acceptance_criteria or []),
            verification_hooks=hooks,
        )
        vault: VaultLike = _PathOnlyVault(self._vault_path)
        path = write_spec_note_canonical(data, vault=vault)
        logger.debug("Spec note written: %s", path)

        # SELECTIVE INDEXING — vectorise only this new spec
        rel_path = str(path.relative_to(self._vault_path))
        self._semantic.index_file(rel_path)

        if sync_vault:
            self._semantic.sync()

        # Pluggable Middle — open the Session BEFORE storing the episodic
        # memory entry. Reasoning: opening the session is the operation
        # that follow-up tools (cortex-SDDwork, doctor, the MCP status
        # endpoint) actually depend on. Episodic embedding is best-effort
        # enrichment that may be slow on cold ONNX loads; keeping it
        # downstream means a slow embedder can never delay the active
        # session pointer from being visible to other agents.
        # See the May 2026 ``realestate`` incident for the original
        # symptom (cortex-SDDwork reporting "No active session" while the
        # spec_service was still mid-flight).
        opened_session: SessionRecord | None = None
        if self._session_service is not None:
            try:
                opened_session = self._session_service.open(
                    spec_id=path.stem,
                    spec_path=path,
                    spec_summary=goal or title,
                )
            except Exception as exc:  # pragma: no cover — defensive
                logger.warning(
                    "Spec %s persisted, but failed to open Session: %s",
                    path.name,
                    exc,
                )

        if remember:
            self._store_episodic(
                title=title,
                goal=goal,
                requirements=requirements or [],
                files_in_scope=files_in_scope or [],
                tags=tags or [],
            )

        return SpecCreationResult(path=path, session=opened_session)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_hooks(
        hooks: list[VerificationHook] | list[dict[str, Any]] | None,
    ) -> list[VerificationHook]:
        """Validate + coerce *hooks* into a list of :class:`VerificationHook`.

        Raises ``ValueError`` if two hooks share the same name (data
        integrity is non-negotiable — duplicates are always rejected).
        """
        if not hooks:
            return []
        coerced: list[VerificationHook] = []
        for item in hooks:
            if isinstance(item, VerificationHook):
                coerced.append(item)
            else:
                coerced.append(VerificationHook.model_validate(item))
        names = [h.name for h in coerced]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise ValueError(f"verification_hooks contains duplicate name(s): {duplicates}")
        return coerced

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
