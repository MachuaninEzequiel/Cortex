"""cortex.session.service — Public API for the Session primitive.

This module wires :class:`SessionStorage` (persistence) and the git wrapper
(:mod:`cortex.session.git`) together into a service that callers — the MCP
server, the CLI, the spec service — talk to.

Design notes:
    * :class:`SessionRecord` enforces lifecycle invariants. We re-validate
      on every mutation that changes ``status`` by going through
      ``model_dump → update → model_validate`` rather than direct field
      assignment (which trips the model validator mid-mutation).
    * ``infer_mode`` is a pure static function so it can be tested in
      isolation and reused by the documenter when reconstructing sessions.
    * Collisions on ``session_id`` are resolved by appending ``-2``, ``-3``,
      ... — see :meth:`_make_unique_session_id`. The base id is normally
      the spec stem (``YYYY-MM-DD_<slug>``); appending stays within the
      valid pattern.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from cortex.session import git
from cortex.session.errors import (
    InvalidStateTransition,
    SessionNotFound,
)
from cortex.session.models import (
    GITLESS_COMMIT_PLACEHOLDER,
    Checkpoint,
    CheckpointSource,
    SessionMode,
    SessionRecord,
    SessionStatus,
    Task,
    TaskStatus,
)
from cortex.session.storage import SessionStorage

logger = logging.getLogger(__name__)

# Statuses that may NOT be passed to ``close``: only terminal ones.
_TERMINAL_STATUSES: frozenset[SessionStatus] = frozenset(
    {SessionStatus.CLOSED, SessionStatus.HANDOFF, SessionStatus.ABANDONED}
)

# Sources considered "Cortex agents" for mode inference.
_CORTEX_SOURCES: frozenset[CheckpointSource] = frozenset(
    {
        CheckpointSource.CORTEX_SYNC,
        CheckpointSource.CORTEX_SDDWORK,
        CheckpointSource.CORTEX_CODE_EXPLORER,
        CheckpointSource.CORTEX_CODE_IMPLEMENTER,
    }
)


class SessionService:
    """Public API for managing :class:`SessionRecord` instances.

    The service is stateless beyond its two injected dependencies. Tests
    can pass a temporary :class:`SessionStorage` and a tmp git repo for
    *repo_root*; production callers pass the workspace-aware storage and
    the project's git root.
    """

    def __init__(self, storage: SessionStorage, repo_root: Path) -> None:
        self._storage = storage
        self._repo_root = Path(repo_root)

    # ── Active-session lock for external IDE extensions ───────────

    def _write_session_lock(self, session_id: str | None) -> None:
        """Mantener sincronizado ``<repo_root>/.cortex/session.lock``.

        External IDE extensions bundled with Cortex (notably ``cortex-net.ts``
        en el bundle de Pi 2.5+net) read this file to discover the active
        Cortex session id **without** going through the MCP server. Format:
        the session_id as plain UTF-8 text (no JSON, no frontmatter), with a
        trailing newline. ``cortex-net.ts`` uses ``readFileSync(...).trim()``,
        so the trailing newline is benign.

        Semantics:
            ``session_id is None`` → remove the file if it exists.
            ``session_id is str``  → atomically (best-effort) write the id.

        Best-effort: if the parent directory does not exist (e.g. workspaces
        without ``.cortex/`` setup) and we cannot create it, we log at debug
        and continue. Failing here must NEVER break the session lifecycle —
        the lock is a presentation-layer artifact for external readers, not a
        source of truth.
        """
        lock_path = self._repo_root / ".cortex" / "session.lock"
        try:
            if session_id is None:
                if lock_path.is_file():
                    lock_path.unlink()
                return
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            # ``write_bytes`` para evitar la traduccion CRLF de Windows que
            # ``Path.write_text`` aplica por default. El formato esperado
            # por ``cortex-net.ts`` (y por consistencia cross-platform) es
            # ``<id>\n`` literal.
            lock_path.write_bytes(f"{session_id}\n".encode())
        except OSError:
            logger.debug(
                "Failed to update session.lock at %s", lock_path, exc_info=True
            )

    # ── Read API ──────────────────────────────────────────────────

    def get(self, session_id: str) -> SessionRecord:
        return self._storage.load(session_id)

    def get_active(self) -> SessionRecord | None:
        """Return the active session, or ``None`` when no pointer is set.

        Stale pointers (set but pointing at a missing file) are reported
        as ``None`` so that the CLI degrades gracefully. ``cortex doctor``
        is responsible for surfacing the inconsistency to the user.
        """
        session_id = self._storage.get_active_session_id()
        if session_id is None:
            return None
        try:
            return self._storage.load(session_id)
        except SessionNotFound:
            logger.warning(
                "Active session pointer references missing session %r; "
                "treating as no active session.",
                session_id,
            )
            return None

    def set_active(self, session_id: str) -> None:
        """Promote ``session_id`` to active. Must exist and be OPEN."""
        record = self._storage.load(session_id)
        if record.status is not SessionStatus.OPEN:
            raise InvalidStateTransition(
                f"Cannot set active a session in status {record.status.value!r}; "
                "only OPEN sessions can be active."
            )
        self._storage.set_active_session_id(session_id)
        self._write_session_lock(session_id)

    def list(self, status: SessionStatus | None = None) -> list[SessionRecord]:
        if status is None:
            return self._storage.list_all()
        return self._storage.list_by_status(status)

    # ── Lifecycle: open / checkpoint / close / abandon ────────────

    def open(
        self,
        *,
        spec_id: str,
        spec_path: Path,
        spec_summary: str = "",
    ) -> SessionRecord:
        """Create a new OPEN Session for ``spec_id`` and set it as active.

        ``spec_id`` is the canonical stem of the spec file
        (``YYYY-MM-DD_<slug>``). When that id already exists in storage,
        the service appends a ``-2``, ``-3``, ... suffix to keep the
        record unique without raising.

        Captures the current HEAD SHA and branch name from
        ``self._repo_root`` when git is available. If the workspace
        lacks git (``is_git_repo`` returns False) or git is otherwise
        unusable (timeout, corruption), the session is opened in
        **gitless mode**: ``start_commit`` is set to
        :data:`cortex.session.models.GITLESS_COMMIT_PLACEHOLDER`,
        ``start_branch`` to an empty string, and a structured warning
        is logged. The documenter detects the sentinel at close time
        and falls back to a checkpoint-only reconstruction.

        Idempotency: if a session with ``session_id == spec_id`` already
        exists AND is still OPEN, the existing record is returned without
        creating a new one. This prevents client-side retries (e.g. MCP
        client timeouts on ``cortex_create_spec`` while the server-side
        ``open`` completed) from spawning ghost ``-2``, ``-3``... sessions.
        Only CLOSED/HANDOFF/ABANDONED collisions allocate a new suffixed id.
        See ``docs/incidents/2026-05-22_appfutbol-mcp-duplicate-loop/``.
        """
        if self._storage.exists(spec_id):
            try:
                existing = self._storage.load(spec_id)
            except Exception:  # noqa: BLE001 — storage corruption shouldn't block opens
                existing = None
            if existing is not None and existing.status is SessionStatus.OPEN:
                self._storage.set_active_session_id(existing.session_id)
                self._write_session_lock(existing.session_id)
                return existing
        session_id = self._make_unique_session_id(spec_id)
        if git.is_git_repo(self._repo_root):
            start_commit = git.get_head_commit(self._repo_root)
            start_branch = git.get_current_branch(self._repo_root)
        else:
            start_commit = GITLESS_COMMIT_PLACEHOLDER
            start_branch = ""
            logger.warning(
                "Opening session %s in gitless mode (no git repository at %s). "
                "Documenter will reconstruct from checkpoints only.",
                session_id,
                self._repo_root,
            )
        record = SessionRecord(
            session_id=session_id,
            spec_path=Path(spec_path),
            spec_summary=spec_summary,
            start_commit=start_commit,
            start_branch=start_branch,
            opened_at=datetime.now(UTC),
        )
        self._storage.save_new(record)
        self._storage.set_active_session_id(session_id)
        self._write_session_lock(session_id)
        if record.is_gitless:
            logger.info("Opened session %s in gitless mode", session_id)
        else:
            logger.info(
                "Opened session %s on branch %s @ %s",
                session_id,
                start_branch,
                start_commit[:8],
            )
        return record

    def checkpoint(
        self,
        session_id: str,
        *,
        source: CheckpointSource,
        verified_claims: Sequence[str] = (),
        unverified_claims: Sequence[str] = (),
        artifacts_touched: Sequence[str] = (),
        note: str = "",
    ) -> SessionRecord:
        """Append a checkpoint to an OPEN session."""
        record = self._storage.load(session_id)
        if record.status is not SessionStatus.OPEN:
            raise InvalidStateTransition(
                f"Cannot append checkpoint to session in status {record.status.value!r}"
            )
        cp = Checkpoint(
            timestamp=datetime.now(UTC),
            source=source,
            verified_claims=list(verified_claims),
            unverified_claims=list(unverified_claims),
            artifacts_touched=list(artifacts_touched),
            note=note,
        )
        record.checkpoints.append(cp)
        self._storage.save(record)
        return record

    def close(
        self,
        session_id: str,
        *,
        status: SessionStatus,
        documenter_decision: SessionStatus,
        session_note_path: Path | None = None,
        adrs_created: Iterable[Path] = (),
    ) -> SessionRecord:
        """Close an OPEN session into a terminal status.

        ``status`` must be one of CLOSED / HANDOFF / ABANDONED. Captures
        HEAD as ``end_commit``, infers the mode from existing checkpoints,
        clears the active pointer when it pointed to this session.
        """
        if status not in _TERMINAL_STATUSES:
            raise ValueError(
                f"status passed to close() must be terminal "
                f"(CLOSED | HANDOFF | ABANDONED), got {status!r}"
            )
        record = self._storage.load(session_id)
        if record.status is not SessionStatus.OPEN:
            raise InvalidStateTransition(f"Cannot close session in status {record.status.value!r}")

        # Gitless sessions reuse the placeholder for ``end_commit`` so the
        # close path doesn't fail and the documenter still has a sentinel
        # to branch on. Git-aware sessions capture HEAD as usual.
        if record.is_gitless:
            end_commit = GITLESS_COMMIT_PLACEHOLDER
        else:
            end_commit = git.get_head_commit(self._repo_root)
        mode = self.infer_mode(record.checkpoints)

        data = record.model_dump(mode="python")
        data.update(
            {
                "status": status,
                "mode": mode,
                "closed_at": datetime.now(UTC),
                "end_commit": end_commit,
                "documenter_decision": documenter_decision,
                "session_note_path": Path(session_note_path) if session_note_path else None,
                "adrs_created": [Path(p) for p in adrs_created],
            }
        )
        updated = SessionRecord.model_validate(data)
        self._storage.save(updated)
        if self._storage.get_active_session_id() == session_id:
            self._storage.set_active_session_id(None)
            self._write_session_lock(None)
        logger.info(
            "Closed session %s as %s (mode=%s, end=%s)",
            session_id,
            status.value,
            mode.value,
            end_commit[:8],
        )
        return updated

    def abandon(self, session_id: str, *, reason: str = "") -> SessionRecord:
        """Convenience: append a MANUAL checkpoint with the reason and close as ABANDONED."""
        record = self._storage.load(session_id)
        if record.status is SessionStatus.OPEN and reason:
            self.checkpoint(
                session_id,
                source=CheckpointSource.MANUAL,
                note=f"Abandoned: {reason}",
            )
        return self.close(
            session_id,
            status=SessionStatus.ABANDONED,
            documenter_decision=SessionStatus.ABANDONED,
        )

    # ── Task management (Pluggable Middle Phase 09.C) ────────────

    def add_task(self, session_id: str, task: Task) -> SessionRecord:
        """Append a :class:`Task` to ``SessionRecord.tasks``.

        Raises :class:`InvalidStateTransition` if the session is not
        OPEN, or :class:`ValueError` if a task with the same id already
        exists (task ids are unique within a session).
        """
        record = self._storage.load(session_id)
        if record.status is not SessionStatus.OPEN:
            raise InvalidStateTransition(
                f"Cannot add task to session in status {record.status.value!r}"
            )
        if any(t.id == task.id for t in record.tasks):
            raise ValueError(f"Task id {task.id!r} already exists in session {session_id!r}")
        record.tasks.append(task)
        self._storage.save(record)
        return record

    def update_task_status(
        self,
        session_id: str,
        task_id: str,
        new_status: TaskStatus,
        *,
        note: str = "",
        checkpoint_index: int | None = None,
    ) -> SessionRecord:
        """Mutate one task's ``status`` (and optional ``note`` / link).

        For terminal statuses (``done`` / ``skipped`` / ``blocked``) we
        stamp ``completed_at`` automatically when the caller didn't
        already set one — keeps the invariant ``Task.status='done' ⇒
        completed_at is not None`` enforced by the model.
        """
        record = self._storage.load(session_id)
        if record.status is not SessionStatus.OPEN:
            raise InvalidStateTransition(
                f"Cannot update task in session with status {record.status.value!r}"
            )
        for idx, task in enumerate(record.tasks):
            if task.id != task_id:
                continue
            data = task.model_dump(mode="python")
            data["status"] = new_status
            if note:
                data["note"] = note
            if checkpoint_index is not None:
                data["checkpoint_index"] = checkpoint_index
            if new_status is TaskStatus.DONE:
                data["completed_at"] = data.get("completed_at") or datetime.now(UTC)
            elif new_status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
                data["completed_at"] = None
            record.tasks[idx] = Task.model_validate(data)
            self._storage.save(record)
            return record
        raise ValueError(f"Task id {task_id!r} not found in session {session_id!r}")

    def list_tasks(
        self,
        session_id: str,
        status: TaskStatus | None = None,
    ) -> Sequence[Task]:
        """Return the session tasks, optionally filtered by ``status``."""
        record = self._storage.load(session_id)
        if status is None:
            return list(record.tasks)
        return [t for t in record.tasks if t.status is status]

    # ── Diff inspection ──────────────────────────────────────────

    def compute_diff(self, session_id: str) -> str:
        """Return ``git diff <start_commit>..<end_ref>`` for the session.

        Uses ``end_commit`` when the session is closed, ``HEAD`` otherwise.
        Returns an empty string for sessions opened in gitless mode — the
        documenter inspects checkpoints instead.
        """
        record = self._storage.load(session_id)
        if record.is_gitless:
            return ""
        end_ref = record.end_commit if record.end_commit else "HEAD"
        return git.diff(record.start_commit, end_ref, self._repo_root)

    # ── Mode inference (pure static helper) ─────────────────────

    @staticmethod
    def infer_mode(checkpoints: Sequence[Checkpoint]) -> SessionMode:
        """Infer the session :class:`SessionMode` from its checkpoints.

        - **No checkpoints** → :attr:`SessionMode.BYO`.
        - **Every source is CI_BOT** → :attr:`SessionMode.CI_REVIEW`
          (Phase 07 Level 3).
        - **All other sources are Cortex agents** → :attr:`SessionMode.MANAGED`.
        - **Anything else** (IDE hook, user skill, manual, or a mix) →
          :attr:`SessionMode.OBSERVED`.
        """
        if not checkpoints:
            return SessionMode.BYO
        sources = {cp.source for cp in checkpoints}
        if sources == {CheckpointSource.CI_BOT}:
            return SessionMode.CI_REVIEW
        if sources.issubset(_CORTEX_SOURCES):
            return SessionMode.MANAGED
        return SessionMode.OBSERVED

    # ── Internal helpers ────────────────────────────────────────

    def _make_unique_session_id(self, base: str) -> str:
        """Return *base*, or *base*-2, *base*-3, ... if storage has it."""
        if not self._storage.exists(base):
            return base
        counter = 2
        while True:
            candidate = f"{base}-{counter}"
            if not self._storage.exists(candidate):
                return candidate
            counter += 1


__all__ = ["SessionService"]
