"""cortex.autopilot.session_writer — Persist Autopilot drafts to disk.

Bridges the Autopilot lifecycle with durable storage. Before this module,
``AutopilotService.finish`` set ``state.session_note_path`` to a string
but never created the file, breaking the core promise that finishing a
session documents it.

The :class:`SessionWriter` Protocol decouples persistence from lifecycle
logic so that:

* the default :class:`VaultSessionWriter` writes Markdown to
  ``<vault>/sessions/`` using ``WorkspaceLayout``-aware paths,
* unit tests can substitute a no-op or in-memory writer,
* future implementations can pipe writes through ``SessionService`` to
  also index into episodic/semantic memory.
"""
from __future__ import annotations

import logging
import re
from datetime import date as date_cls
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from cortex.autopilot.models import AutopilotSessionState, SessionDraft
from cortex.security.paths import resolve_safe, validate_under_root

if TYPE_CHECKING:
    from cortex.episodic.memory_store import EpisodicMemoryStore
    from cortex.semantic.vault_reader import VaultReader

logger = logging.getLogger(__name__)


_SLUG_STRIP = re.compile(r"[^a-zA-Z0-9\s-]")
_SLUG_SEP = re.compile(r"[\s_-]+")


def _slugify(value: str) -> str:
    slug = _SLUG_STRIP.sub("", value.strip().lower())
    slug = _SLUG_SEP.sub("-", slug).strip("-")
    return slug or "autopilot-session"


@runtime_checkable
class SessionWriter(Protocol):
    """Persist an Autopilot ``SessionDraft`` to durable storage.

    Implementations must return the absolute path where the draft was
    written. If persistence fails, the implementation must raise an
    exception so that ``AutopilotService`` does not mark the session as
    documented.
    """

    def write(self, state: AutopilotSessionState, draft: SessionDraft) -> Path: ...


class VaultSessionWriter:
    """Default writer that persists Autopilot drafts to ``<vault>/sessions/``.

    Each draft becomes a Markdown file with frontmatter plus the rendered
    body. The filename is ``<YYYY-MM-DD>_<session_id>_<slug>.md`` so
    multiple Autopilot sessions in a single day never collide.

    This writer does not index the note into episodic/semantic memory.
    Callers wanting indexing should run ``cortex sync-vault`` afterwards
    or inject a writer that wraps :class:`~cortex.services.SessionService`.
    """

    def __init__(self, vault_path: Path) -> None:
        self._vault_path = Path(vault_path)

    @property
    def vault_path(self) -> Path:
        return self._vault_path

    def write(self, state: AutopilotSessionState, draft: SessionDraft) -> Path:
        today = date_cls.today()
        target_dir = resolve_safe(self._vault_path, "sessions")
        target_dir.mkdir(parents=True, exist_ok=True)

        slug_source = draft.title or state.title_hint or "autopilot-session"
        filename = f"{today.isoformat()}_{state.session_id}_{_slugify(slug_source)}.md"
        path = validate_under_root(target_dir / filename, self._vault_path)

        path.write_text(self._render(state, draft, today), encoding="utf-8")
        return path

    @staticmethod
    def _render(
        state: AutopilotSessionState,
        draft: SessionDraft,
        today: date_cls,
    ) -> str:
        tags = ["session", "autopilot"]
        if draft.confidence == "auto-draft":
            tags.append("auto-draft")

        frontmatter_lines = [
            "---",
            f'title: "{_escape_yaml_string(draft.title)}"',
            f"date: {today.isoformat()}",
            f"tags: [{', '.join(tags)}]",
            f"status: {state.status}",
            f"session_id: {state.session_id}",
            f"mode: {state.mode}",
            f"confidence: {draft.confidence}",
        ]
        if state.detected_task_type:
            frontmatter_lines.append(f"task_type: {state.detected_task_type}")
        if state.complexity:
            frontmatter_lines.append(f"complexity: {state.complexity}")
        frontmatter_lines.extend(["---", ""])

        body = draft.body.strip() if draft.body else "(no body recorded)"

        sections = [
            "\n".join(frontmatter_lines),
            f"# {draft.title}",
            "",
            body,
        ]

        if draft.warnings:
            sections.extend(
                [
                    "",
                    "## Warnings",
                    *(f"- {w}" for w in draft.warnings),
                ]
            )

        return "\n".join(sections) + "\n"


def _escape_yaml_string(value: str) -> str:
    """Escape double quotes inside a YAML double-quoted string."""
    return value.replace('"', '\\"')


class IndexingSessionWriter:
    """``SessionWriter`` decorator that indexes every persisted note.

    Wraps a base ``SessionWriter`` (typically :class:`VaultSessionWriter`)
    and, after a successful write, indexes the result into both the
    semantic vault (vector store) and the episodic memory store.

    **Transactional contract**: if any indexing step fails, the persisted
    file is rolled back (unlinked) and the exception propagates. This
    guarantees the invariant ``file on disk ⇒ file indexed``. No orphan
    notes can be created.

    Indexing is mandatory whenever Autopilot writes documentation. This
    is the user-facing promise of Cortex: every documented artifact is
    immediately retrievable via ``cortex search``.
    """

    def __init__(
        self,
        inner: SessionWriter,
        vault_path: Path,
        semantic: "VaultReader",
        episodic: "EpisodicMemoryStore",
        context_metadata: dict[str, str] | None = None,
    ) -> None:
        self._inner = inner
        self._vault_path = Path(vault_path)
        self._semantic = semantic
        self._episodic = episodic
        self._context_metadata = dict(context_metadata or {})

    @property
    def vault_path(self) -> Path:
        return self._vault_path

    def write(self, state: AutopilotSessionState, draft: SessionDraft) -> Path:
        path = self._inner.write(state, draft)
        try:
            self._index(state, draft, path)
        except Exception:
            # Transactional rollback: indexing failed, so the persisted
            # file must not remain on disk. The exception is re-raised
            # so AutopilotService._persist_draft observes the failure
            # and does NOT mark the session as ``documented``.
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:  # pragma: no cover - defensive
                logger.warning(
                    "Indexing rollback failed to unlink %s: %s", path, exc
                )
            raise
        return path

    def _index(
        self,
        state: AutopilotSessionState,
        draft: SessionDraft,
        path: Path,
    ) -> None:
        rel_path = str(path.relative_to(self._vault_path))
        # Step 1 — semantic vector index (selective: only this file).
        self._semantic.index_file(rel_path)
        # Step 2 — episodic memory entry for future retrieval.
        self._episodic.add(
            content=self._build_episodic_content(state, draft),
            memory_type="session",
            tags=self._build_tags(draft, state),
            files=list(state.changed_files),
            extra_metadata=self._build_metadata(state, draft, path),
        )

    @staticmethod
    def _build_episodic_content(
        state: AutopilotSessionState,
        draft: SessionDraft,
    ) -> str:
        parts = [f"Session: {draft.title}"]
        if state.user_request:
            parts.append(f"Request: {state.user_request}")
        if state.detected_task_type:
            parts.append(f"Task type: {state.detected_task_type}")
        if draft.body:
            # Bound the indexed body so a verbose draft doesn't blow up
            # the embedding budget. Full content stays on disk.
            parts.append(draft.body.strip()[:1500])
        return "\n".join(parts)

    @staticmethod
    def _build_tags(
        draft: SessionDraft,
        state: AutopilotSessionState | None = None,
    ) -> list[str]:
        """Build the episodic-memory tag list for the persisted session.

        Adds ``handoff`` when the session closed in handoff mode (Tripartita
        Refinada): the next ``cortex_sync_ticket`` retrieval is expected to
        prioritise these notes via the tag filter.
        """
        tags = ["session", "autopilot"]
        if draft.confidence == "auto-draft":
            tags.append("auto-draft")
        if state is not None and state.status == "handoff":
            tags.append("handoff")
        return tags

    def _build_metadata(
        self,
        state: AutopilotSessionState,
        draft: SessionDraft,
        path: Path,
    ) -> dict[str, str]:
        metadata = dict(self._context_metadata)
        metadata.update(
            {
                "session_id": state.session_id,
                "mode": state.mode,
                "confidence": draft.confidence,
                "session_note_path": str(path),
            }
        )
        if state.detected_task_type:
            metadata["task_type"] = state.detected_task_type
        if state.complexity:
            metadata["complexity"] = state.complexity
        return metadata


def is_indexing_writer(writer: object | None) -> bool:
    """Return True when *writer* persists AND indexes session notes.

    Used by ``cortex autopilot doctor`` to flag degraded setups where
    Autopilot can write notes but cannot make them retrievable.
    """
    return isinstance(writer, IndexingSessionWriter)
