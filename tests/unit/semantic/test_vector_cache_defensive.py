"""Defensive-path tests for VectorCache (Fase 13 backlog cleanup).

Covers the 9 lines flagged in Fase 06 REALIZACION.md as defensive: errors
when the chunks.bin file goes missing, when ``__contains__`` receives a
non-string, when ``invalidate`` is called on an already-invalidated entry,
and the short-read detection inside ``_read_vector_at``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from cortex.semantic.vector_cache import VECTOR_DIM, VectorCache


def _rand() -> np.ndarray:
    return np.random.rand(VECTOR_DIM).astype(np.float32)


# ---------------------------------------------------------------------------
# get() failure path: chunks.bin missing/truncated
# ---------------------------------------------------------------------------


def test_get_handles_missing_chunks_bin(tmp_path: Path) -> None:
    cache_dir = tmp_path / "vectors"
    cache = VectorCache(cache_dir)
    cache.put("fp1", "c", _rand())
    # Delete the binary out of band; the cache should miss instead of crashing.
    (cache_dir / "chunks.bin").unlink()
    assert cache.get("fp1") is None


def test_get_handles_truncated_chunks_bin(tmp_path: Path) -> None:
    cache_dir = tmp_path / "vectors"
    cache = VectorCache(cache_dir)
    cache.put("fp1", "c", _rand())
    # Truncate the bin so the offset is out of range.
    (cache_dir / "chunks.bin").write_bytes(b"")
    assert cache.get("fp1") is None


# ---------------------------------------------------------------------------
# invalidate(): already-invalidated entry must still return True
# ---------------------------------------------------------------------------


def test_invalidate_twice_returns_true(tmp_path: Path) -> None:
    # ``auto_compact=False`` keeps the invalidated entry around so the
    # idempotence contract is observable.
    cache = VectorCache(tmp_path / "vectors", auto_compact=False)
    cache.put("fp1", "c", _rand())
    assert cache.invalidate("fp1") is True
    # Idempotent: second call still returns True because the entry still exists.
    assert cache.invalidate("fp1") is True


# ---------------------------------------------------------------------------
# compact(): unreadable entries are skipped
# ---------------------------------------------------------------------------


def test_compact_skips_unreadable_entries(tmp_path: Path) -> None:
    cache_dir = tmp_path / "vectors"
    cache = VectorCache(cache_dir)
    cache.put("fp1", "c1", _rand())
    cache.put("fp2", "c2", _rand())
    # Corrupt chunks.bin so reads partially fail.
    (cache_dir / "chunks.bin").write_bytes(b"\x00" * 8)
    # Compact must not raise.
    cache.compact()


# ---------------------------------------------------------------------------
# __contains__ with non-string returns False
# ---------------------------------------------------------------------------


def test_contains_non_string_returns_false(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    cache.put("fp1", "c", _rand())
    assert 42 not in cache
    assert None not in cache
    assert object() not in cache


# ---------------------------------------------------------------------------
# _read_vector_at short-read detection
# ---------------------------------------------------------------------------


def test_short_read_raises_value_error(tmp_path: Path) -> None:
    cache_dir = tmp_path / "vectors"
    cache = VectorCache(cache_dir)
    cache.put("fp1", "c", _rand())
    # Truncate so read returns fewer bytes than expected.
    (cache_dir / "chunks.bin").write_bytes(b"\x00" * 10)
    with pytest.raises(ValueError, match="Short read"):
        cache._read_vector_at(0, VECTOR_DIM)
