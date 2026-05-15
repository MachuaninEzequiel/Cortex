"""cortex.semantic.vector_cache - Persistent cache for embedding vectors.

Eliminates the cold-start cost of re-embedding the entire semantic vault on
each process restart. Vectors are stored in a single binary file
(``chunks.bin``) keyed by SHA-256 fingerprint of the embedding text; an
``index.json`` companion file maps fingerprints to (offset, dim) byte
positions.

Layout::

    .cortex/vectors/
        index.json     - { schema_version, entries: {fp: CacheEntry}, invalidated: [fp...] }
        chunks.bin     - contiguous array of float32 vectors

Invalidation triggers:
    1. Fingerprint mismatch (content changed in the file).
    2. ``schema_version`` bump (cache layout changed).
    3. Explicit ``invalidate(fp)`` or ``invalidate_by_chunk_id(prefix)``.

The cache is thread-safe (single-process, RLock). It is **not** safe for
concurrent processes; that's a deliberate trade-off for MVP simplicity.

When invalidations accumulate, call ``compact()`` to reclaim space. The
``CacheStats.invalidated_entries`` field surfaces when compaction is worth it.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

CACHE_SCHEMA_VERSION = 1
VECTOR_DTYPE = np.float32
VECTOR_DIM = 384  # all-MiniLM-L6-v2
_BYTES_PER_VECTOR = VECTOR_DIM * 4  # float32 = 4 bytes


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CacheEntry:
    """A single vector entry persisted in the cache."""

    fingerprint: str
    chunk_id: str
    offset: int   # byte offset in chunks.bin
    dim: int
    schema_version: int


@dataclass
class CacheStats:
    """Operational metrics of the cache."""

    total_entries: int = 0
    valid_entries: int = 0
    invalidated_entries: int = 0
    size_bytes: int = 0
    hit_count: int = 0
    miss_count: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total else 0.0


# ---------------------------------------------------------------------------
# VectorCache
# ---------------------------------------------------------------------------


class VectorCache:
    """Persistent cache for sentence-transformer-style embeddings.

    Args:
        cache_dir: directory where ``index.json`` and ``chunks.bin`` live.

    Example:
        >>> cache = VectorCache(Path(".cortex/vectors"))
        >>> vec = np.random.rand(384).astype(np.float32)
        >>> cache.put("fingerprint-hash", "decisions/ADR-007.md", vec)
        >>> got = cache.get("fingerprint-hash")
    """

    def __init__(
        self,
        cache_dir: Path,
        *,
        auto_compact: bool = True,
        auto_compact_threshold: float = 0.30,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.cache_dir / "index.json"
        self._bin_path = self.cache_dir / "chunks.bin"
        self._lock = threading.RLock()
        self._index: dict[str, CacheEntry] = {}
        self._invalidated: set[str] = set()
        self._hit_count = 0
        self._miss_count = 0
        self._auto_compact = bool(auto_compact)
        if not 0.0 < auto_compact_threshold <= 1.0:
            raise ValueError(
                f"auto_compact_threshold must be in (0, 1], got {auto_compact_threshold!r}"
            )
        self._auto_compact_threshold = float(auto_compact_threshold)
        self._load()

    # ------------------------------------------------------------------
    # Auto-compaction helper (Item #3 PLAN-DEUDA-RESIDUAL).
    # ------------------------------------------------------------------

    def _maybe_auto_compact(self) -> None:
        """Trigger ``compact()`` when invalidated entries cross the threshold.

        Caller must hold ``self._lock``. Skipped when auto-compaction is
        disabled or the cache is empty.
        """
        if not self._auto_compact:
            return
        total = len(self._index)
        if total == 0:
            return
        if (len(self._invalidated) / total) >= self._auto_compact_threshold:
            self.compact()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load index from disk. Reset cache on schema mismatch or corruption."""
        if not self._index_path.exists():
            return
        try:
            with self._index_path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Vector cache index unreadable, resetting: %s", exc)
            self._reset_corrupt()
            return

        if raw.get("schema_version") != CACHE_SCHEMA_VERSION:
            logger.info(
                "Vector cache schema mismatch (got %s, expected %s); resetting",
                raw.get("schema_version"), CACHE_SCHEMA_VERSION,
            )
            self._reset_corrupt()
            return

        try:
            self._index = {
                fp: CacheEntry(**entry) for fp, entry in raw.get("entries", {}).items()
            }
            self._invalidated = set(raw.get("invalidated", []))
        except (KeyError, TypeError) as exc:
            logger.warning("Vector cache index malformed, resetting: %s", exc)
            self._reset_corrupt()

    def _reset_corrupt(self) -> None:
        self._index = {}
        self._invalidated = set()
        if self._bin_path.exists():
            try:
                self._bin_path.unlink()
            except OSError:  # pragma: no cover - defensive
                pass

    def _save_index(self) -> None:
        """Persist index.json atomically (tmp + rename)."""
        data = {
            "schema_version": CACHE_SCHEMA_VERSION,
            "entries": {fp: asdict(e) for fp, e in self._index.items()},
            "invalidated": sorted(self._invalidated),
        }
        tmp_path = self._index_path.with_suffix(".tmp")
        try:
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(data, f)
            tmp_path.replace(self._index_path)
        except OSError as exc:  # pragma: no cover - defensive
            logger.warning("Vector cache index save failed: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, fingerprint: str) -> np.ndarray | None:
        """Return vector for ``fingerprint`` or ``None`` on miss/invalidated."""
        with self._lock:
            entry = self._index.get(fingerprint)
            if entry is None or fingerprint in self._invalidated:
                self._miss_count += 1
                return None
            try:
                vec = self._read_vector_at(entry.offset, entry.dim)
            except (OSError, ValueError) as exc:
                logger.warning(
                    "Vector cache read failed for %s: %s",
                    fingerprint[:16], exc,
                )
                self._miss_count += 1
                return None
            self._hit_count += 1
            return vec

    def put(self, fingerprint: str, chunk_id: str, vector: np.ndarray) -> None:
        """Store ``vector`` under ``fingerprint`` / ``chunk_id``.

        If ``fingerprint`` already exists, the old entry is invalidated and a
        fresh copy is appended. Use ``compact()`` to reclaim space.
        """
        if vector.dtype != VECTOR_DTYPE:
            vector = vector.astype(VECTOR_DTYPE)
        if vector.shape != (VECTOR_DIM,):
            raise ValueError(
                f"Expected vector shape ({VECTOR_DIM},), got {vector.shape}"
            )

        with self._lock:
            if fingerprint in self._index:
                self._invalidated.add(fingerprint)

            try:
                offset = self._bin_path.stat().st_size if self._bin_path.exists() else 0
                with self._bin_path.open("ab") as f:
                    f.write(vector.tobytes())
            except OSError as exc:  # pragma: no cover - defensive
                logger.warning("Vector cache write failed: %s", exc)
                return

            self._index[fingerprint] = CacheEntry(
                fingerprint=fingerprint,
                chunk_id=chunk_id,
                offset=offset,
                dim=VECTOR_DIM,
                schema_version=CACHE_SCHEMA_VERSION,
            )
            self._invalidated.discard(fingerprint)
            self._save_index()

    def batch_get(self, fingerprints: list[str]) -> dict[str, np.ndarray]:
        """Bulk get. Returns only hits."""
        results: dict[str, np.ndarray] = {}
        for fp in fingerprints:
            vec = self.get(fp)
            if vec is not None:
                results[fp] = vec
        return results

    def batch_put(self, items: list[tuple[str, str, np.ndarray]]) -> None:
        """Bulk put. items = list of (fingerprint, chunk_id, vector)."""
        for fp, cid, vec in items:
            self.put(fp, cid, vec)

    def invalidate(self, fingerprint: str) -> bool:
        """Mark an entry as invalidated. Returns ``True`` if it existed."""
        with self._lock:
            if fingerprint in self._index and fingerprint not in self._invalidated:
                self._invalidated.add(fingerprint)
                self._save_index()
                self._maybe_auto_compact()
                return True
            if fingerprint in self._index:
                # Already invalidated.
                return True
            return False

    def get_chunk_fingerprints(self, parent_path: str) -> dict[str, str]:
        """Return ``{chunk_id: fingerprint}`` for every chunk under ``parent_path``.

        Used by ``VaultReader`` to do granular invalidation: only purge cache
        entries for chunk_ids that no longer exist in the re-parsed document
        (Item #4 PLAN-DEUDA-RESIDUAL).
        """
        prefix_sep = parent_path + "#"
        with self._lock:
            out: dict[str, str] = {}
            for fp, entry in self._index.items():
                if fp in self._invalidated:
                    continue
                if entry.chunk_id == parent_path or entry.chunk_id.startswith(prefix_sep):
                    out[entry.chunk_id] = fp
            return out

    def invalidate_chunks(self, chunk_ids: list[str]) -> int:
        """Invalidate cache entries by exact ``chunk_id`` match.

        Returns the count of newly invalidated entries. Idempotent: re-marking
        an already-invalidated entry is a no-op.
        """
        if not chunk_ids:
            return 0
        targets = set(chunk_ids)
        with self._lock:
            count = 0
            for fp, entry in self._index.items():
                if entry.chunk_id in targets and fp not in self._invalidated:
                    self._invalidated.add(fp)
                    count += 1
            if count > 0:
                self._save_index()
                self._maybe_auto_compact()
            return count

    def invalidate_by_chunk_id(self, chunk_id_prefix: str) -> int:
        """Invalidate every entry whose ``chunk_id`` starts with ``chunk_id_prefix``.

        Useful when a parent document is re-indexed: all its chunks must go.

        Returns the count of newly invalidated entries.
        """
        with self._lock:
            count = 0
            for fp, entry in list(self._index.items()):
                if entry.chunk_id.startswith(chunk_id_prefix) and fp not in self._invalidated:
                    self._invalidated.add(fp)
                    count += 1
            if count > 0:
                self._save_index()
                self._maybe_auto_compact()
            return count

    def compact(self) -> None:
        """Rebuild ``chunks.bin`` keeping only non-invalidated entries.

        Atomic: writes to a temp file, then renames over ``chunks.bin``.
        """
        with self._lock:
            valid = {fp: e for fp, e in self._index.items() if fp not in self._invalidated}
            if not valid and not self._bin_path.exists():
                return

            # Read all valid vectors in current order.
            vectors: dict[str, np.ndarray] = {}
            for fp, entry in valid.items():
                try:
                    vectors[fp] = self._read_vector_at(entry.offset, entry.dim)
                except (OSError, ValueError) as exc:
                    logger.warning(
                        "Skipping unreadable entry %s during compact: %s",
                        fp[:16], exc,
                    )

            tmp_bin = self._bin_path.with_suffix(".tmp")
            new_index: dict[str, CacheEntry] = {}
            try:
                with tmp_bin.open("wb") as f:
                    for fp, vec in vectors.items():
                        offset = f.tell()
                        f.write(vec.tobytes())
                        new_index[fp] = CacheEntry(
                            fingerprint=fp,
                            chunk_id=valid[fp].chunk_id,
                            offset=offset,
                            dim=VECTOR_DIM,
                            schema_version=CACHE_SCHEMA_VERSION,
                        )
                tmp_bin.replace(self._bin_path)
            except OSError as exc:  # pragma: no cover - defensive
                logger.warning("Vector cache compact failed: %s", exc)
                tmp_bin.unlink(missing_ok=True)
                return

            self._index = new_index
            self._invalidated = set()
            self._save_index()

    def clear(self) -> None:
        """Remove all entries and delete the binary file."""
        with self._lock:
            self._index.clear()
            self._invalidated.clear()
            self._hit_count = 0
            self._miss_count = 0
            if self._bin_path.exists():
                try:
                    self._bin_path.unlink()
                except OSError:  # pragma: no cover - defensive
                    pass
            self._save_index()

    def stats(self) -> CacheStats:
        with self._lock:
            size = self._bin_path.stat().st_size if self._bin_path.exists() else 0
            return CacheStats(
                total_entries=len(self._index),
                valid_entries=len(self._index) - len(self._invalidated),
                invalidated_entries=len(self._invalidated),
                size_bytes=size,
                hit_count=self._hit_count,
                miss_count=self._miss_count,
            )

    def __len__(self) -> int:
        with self._lock:
            return len(self._index) - len(self._invalidated)

    def __contains__(self, fingerprint: object) -> bool:
        with self._lock:
            if not isinstance(fingerprint, str):
                return False
            return (
                fingerprint in self._index and fingerprint not in self._invalidated
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_vector_at(self, offset: int, dim: int) -> np.ndarray:
        """Read a single vector from chunks.bin at the given byte offset."""
        nbytes = dim * 4  # float32
        with self._bin_path.open("rb") as f:
            f.seek(offset)
            data = f.read(nbytes)
        if len(data) != nbytes:
            raise ValueError(
                f"Short read at offset {offset}: got {len(data)} bytes, expected {nbytes}"
            )
        return np.frombuffer(data, dtype=VECTOR_DTYPE).copy()


__all__ = [
    "CACHE_SCHEMA_VERSION",
    "VECTOR_DIM",
    "VECTOR_DTYPE",
    "CacheEntry",
    "CacheStats",
    "VectorCache",
]
