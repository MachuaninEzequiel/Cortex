"""cortex.session.storage — File-based persistence for ``SessionRecord``.

Layout::

    .cortex/sessions/
        <session_id>.yaml      # one file per session
        active.txt             # single line: id of the currently active session

Atomicity:
    Every write goes through a temporary file followed by :func:`os.replace`,
    which is atomic on POSIX and on Windows NTFS. Interrupted writes leave
    the previous content intact (or no file at all, for first writes).

Concurrency:
    The MCP server runs tool calls in a ``ThreadPoolExecutor`` (up to
    ``CORTEX_MCP_MAX_WORKERS`` workers, default 4). Clients that double-dispatch
    requests (observed with the Pi client) trigger parallel writes against the
    same session file. We serialize writes per final-path with a process-wide
    lock map (:func:`_path_lock`) and wrap :func:`os.replace` in a short retry
    loop (:func:`_atomic_replace`) to survive transient Windows sharing
    violations from antivirus / indexer scans. See
    ``docs/incidents/2026-05-22_appfutbol-mcp-duplicate-loop/``.

Corrupted files:
    ``list_all`` and ``list_by_status`` log a warning and skip any
    ``*.yaml`` whose content fails to parse, instead of raising. The
    explicit ``load`` operation raises :class:`SessionStorageCorrupted`
    when a specific id cannot be parsed.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable
from pathlib import Path

import yaml

from cortex.session.errors import (
    SessionAlreadyExists,
    SessionNotFound,
    SessionStorageCorrupted,
)
from cortex.session.models import SessionRecord, SessionStatus

logger = logging.getLogger(__name__)

# Public constants for callers / tests.
SESSION_FILE_SUFFIX = ".yaml"
ACTIVE_POINTER_FILENAME = "active.txt"
_TMP_SUFFIX = ".yaml.tmp"
# Edad máxima de un tmp antes de considerarlo huérfano de un crash (V12).
_TMP_MAX_AGE_SECONDS = 3600.0

# Per-final-path locks. Granularity is the destination file (not the
# session_id), so two different sessions can write in parallel; only the
# same session serializes. The map itself is guarded by ``_PATH_LOCKS_MUTEX``.
# ``RLock`` because :meth:`SessionStorage.mutate` holds the lock across
# ``load + fn + save`` and ``save`` re-acquires it on the same thread.
_PATH_LOCKS: dict[str, threading.RLock] = {}
_PATH_LOCKS_MUTEX = threading.Lock()


def _path_lock(path: Path) -> threading.RLock:
    """Return the process-wide reentrant lock that guards writes to ``path``."""
    key = str(path)
    with _PATH_LOCKS_MUTEX:
        lock = _PATH_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _PATH_LOCKS[key] = lock
        return lock


def _is_transient_replace_error(exc: OSError) -> bool:
    """Return True for OS errors that justify an ``os.replace`` retry.

    Windows: ERROR_ACCESS_DENIED (5) and ERROR_SHARING_VIOLATION (32) happen
    when antivirus / indexer / another thread holds an open handle on the
    destination. Both clear within tens of milliseconds in practice.

    POSIX: EACCES (13) and EBUSY (16) are the closest equivalents and are
    benign on rename in the rare cases they surface (FUSE, etc.).
    """
    winerror = getattr(exc, "winerror", None)
    if winerror in (5, 32):
        return True
    return exc.errno in (13, 16)


def _atomic_replace(
    tmp: Path,
    dst: Path,
    *,
    max_attempts: int = 5,
    initial_delay: float = 0.05,
) -> None:
    """``os.replace`` with bounded retry on transient OS errors.

    Behavior matches ``os.replace`` for the success path. On a transient
    failure (see :func:`_is_transient_replace_error`) we sleep with exponential
    backoff (capped) and retry. Non-transient errors propagate immediately.
    """
    delay = initial_delay
    for attempt in range(1, max_attempts + 1):
        try:
            os.replace(tmp, dst)
            return
        except OSError as exc:
            if not _is_transient_replace_error(exc) or attempt == max_attempts:
                raise
            logger.warning(
                "os.replace(%s -> %s) failed transiently (%s); "
                "retry %d/%d after %.0fms",
                tmp.name,
                dst.name,
                exc,
                attempt,
                max_attempts,
                delay * 1000,
            )
            time.sleep(delay)
            delay = min(delay * 2, 0.5)


class SessionStorage:
    """File-based persistence for :class:`SessionRecord`.

    All operations are local I/O — no caching. The expected per-session
    file size is < 10 KB, so reading the directory on demand is cheap.
    """

    def __init__(self, sessions_dir: Path) -> None:
        self._dir = Path(sessions_dir)

    # ── Paths ──────────────────────────────────────────────────────

    @property
    def root(self) -> Path:
        """The sessions directory. Created on demand by ``save``."""
        return self._dir

    def _file_for(self, session_id: str) -> Path:
        return self._dir / f"{session_id}{SESSION_FILE_SUFFIX}"

    # ── Superficie pública (consumida fuera del paquete session) ──

    def file_path(self, session_id: str) -> Path:
        """Ruta canónica del YAML de una sesión (lectura/watchers)."""
        return self._file_for(session_id)

    def active_pointer_path(self) -> Path:
        """Ruta del puntero de sesión activa (``active.txt``)."""
        return self._active_pointer()

    def _tmp_file_for(self, session_id: str) -> Path:
        return self._dir / f"{session_id}{_TMP_SUFFIX}"

    def _gc_orphan_tmps(self) -> None:
        """Eliminar ``*.yaml.tmp`` con más de ``_TMP_MAX_AGE_SECONDS``.

        Un crash entre ``open(tmp)`` y ``os.replace`` deja un tmp huérfano
        que vivía para siempre (deuda V12). Los recientes se conservan:
        puede haber un writer activo a mitad de su ventana de escritura.
        """
        ahora = time.time()
        try:
            huerfanos = list(self._dir.glob(f"*{_TMP_SUFFIX}"))
        except OSError:
            return
        for tmp_path in huerfanos:
            try:
                if ahora - tmp_path.stat().st_mtime > _TMP_MAX_AGE_SECONDS:
                    tmp_path.unlink()
                    logger.debug("GC: tmp huérfano eliminado: %s", tmp_path.name)
            except OSError:  # carrera benigna con otro worker
                continue

    def _active_pointer(self) -> Path:
        return self._dir / ACTIVE_POINTER_FILENAME

    # ── Session record I/O ─────────────────────────────────────────

    def save(self, record: SessionRecord) -> Path:
        """Persist ``record`` atomically. Overwrites any existing file.

        Returns the final file path.
        """
        self._ensure_dir()
        self._gc_orphan_tmps()
        final = self._file_for(record.session_id)
        tmp = self._tmp_file_for(record.session_id)

        payload = record.model_dump(mode="json")
        text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)

        # Serialize concurrent writers on the same final path. Without this,
        # two ThreadPoolExecutor workers racing on the same session_id can
        # both write to the same ``.tmp`` and one of the ``os.replace`` calls
        # fails with ERROR_SHARING_VIOLATION on Windows. The lock is per
        # final-path, so unrelated sessions never block each other.
        with _path_lock(final):
            # Write to tmp, fsync, then atomic rename. If we crash mid-write
            # the tmp file remains (orphan) but ``final`` is never partially
            # written.
            with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
                fh.flush()
                os.fsync(fh.fileno())

            _atomic_replace(tmp, final)
        logger.debug("Saved session %s to %s", record.session_id, final)
        return final

    def mutate(
        self,
        session_id: str,
        fn: Callable[[SessionRecord], SessionRecord | None],
    ) -> SessionRecord:
        """Transactional load→mutate→save under the per-path lock.

        Loads the record, applies ``fn`` to it (``fn`` may mutate in place
        or return a replacement; returning ``None`` keeps the mutated
        record), then saves — all while holding the same per-final-path
        lock used by :meth:`save`. This closes the lost-update window that
        exists when callers do an unlocked ``load`` followed by ``save``:
        two concurrent MCP workers mutating the same session can no longer
        overwrite each other's changes.

        Exceptions raised by ``fn`` propagate and nothing is saved.
        """
        with _path_lock(self._file_for(session_id)):
            record = self.load(session_id)
            result = fn(record)
            if result is not None:
                record = result
            self.save(record)
        return record

    def save_new(self, record: SessionRecord) -> Path:
        """Persist ``record`` and refuse to overwrite an existing file.

        Raises :class:`SessionAlreadyExists` if the destination already
        exists. Use this in code paths that need create-or-fail semantics.
        """
        if self.exists(record.session_id):
            raise SessionAlreadyExists(record.session_id)
        return self.save(record)

    def load(self, session_id: str) -> SessionRecord:
        """Read and validate a session by id.

        Raises:
            SessionNotFound: when the file does not exist.
            SessionStorageCorrupted: when the YAML is unparseable or fails
                schema validation.
        """
        path = self._file_for(session_id)
        if not path.is_file():
            raise SessionNotFound(session_id)
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise SessionStorageCorrupted(f"{path}: invalid YAML — {exc}") from exc

        if not isinstance(data, dict):
            raise SessionStorageCorrupted(
                f"{path}: expected mapping at root, got {type(data).__name__}"
            )

        try:
            return SessionRecord.model_validate(data)
        except Exception as exc:  # pragma: no cover — ValidationError variants
            raise SessionStorageCorrupted(f"{path}: {exc}") from exc

    def exists(self, session_id: str) -> bool:
        return self._file_for(session_id).is_file()

    def delete(self, session_id: str) -> None:
        """Remove the session file.

        Raises :class:`SessionNotFound` if the file does not exist. Clears
        the active pointer if it was pointing at this session.
        """
        path = self._file_for(session_id)
        if not path.is_file():
            raise SessionNotFound(session_id)
        path.unlink()
        if self.get_active_session_id() == session_id:
            self.set_active_session_id(None)

    # ── Listing ────────────────────────────────────────────────────

    def list_all(self) -> list[SessionRecord]:
        """Return every session on disk that can be parsed.

        Files that fail to parse are skipped with a WARNING log entry —
        they don't break the listing. Use :meth:`load` to surface the
        underlying error for a specific id.
        """
        if not self._dir.is_dir():
            return []
        records: list[SessionRecord] = []
        for path in sorted(self._dir.glob(f"*{SESSION_FILE_SUFFIX}")):
            try:
                records.append(self.load(path.stem))
            except SessionStorageCorrupted as exc:
                logger.warning("Skipping corrupted session %s: %s", path.name, exc)
        return records

    def list_by_status(self, status: SessionStatus) -> list[SessionRecord]:
        return [r for r in self.list_all() if r.status is status]

    # ── Active pointer ─────────────────────────────────────────────

    def get_active_session_id(self) -> str | None:
        """Return the id of the active session, or ``None`` if unset."""
        path = self._active_pointer()
        if not path.is_file():
            return None
        content = path.read_text(encoding="utf-8").strip()
        return content or None

    def set_active_session_id(self, session_id: str | None) -> None:
        """Set / clear the active pointer atomically.

        Passing ``None`` removes the file. Calling repeatedly with ``None``
        is a no-op (idempotent).
        """
        path = self._active_pointer()
        if session_id is None:
            if path.is_file():
                path.unlink()
            return

        self._ensure_dir()
        tmp = path.with_suffix(".txt.tmp")
        with _path_lock(path):
            with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(session_id)
                fh.flush()
                os.fsync(fh.fileno())
            _atomic_replace(tmp, path)

    # ── Internal ───────────────────────────────────────────────────

    def _ensure_dir(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)


__all__ = [
    "ACTIVE_POINTER_FILENAME",
    "SESSION_FILE_SUFFIX",
    "SessionStorage",
]
