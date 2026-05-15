"""Tests for cortex.semantic.vector_cache (Fase 06)."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import numpy as np
import pytest

from cortex.semantic.vector_cache import (
    CACHE_SCHEMA_VERSION,
    VECTOR_DIM,
    CacheStats,
    VectorCache,
)


def _rand_vec(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.random(VECTOR_DIM).astype(np.float32)


# ---------------------------------------------------------------------------
# Basic roundtrip
# ---------------------------------------------------------------------------


def test_put_get_roundtrip(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    v = _rand_vec(1)
    cache.put("fp1", "chunk-1", v)
    out = cache.get("fp1")
    assert out is not None
    np.testing.assert_array_equal(out, v)


def test_get_miss_returns_none(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    assert cache.get("unknown") is None


def test_batch_put_get_consistent(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    items = [(f"fp{i}", f"c{i}", _rand_vec(i)) for i in range(5)]
    cache.batch_put(items)
    results = cache.batch_get([f"fp{i}" for i in range(5)] + ["nope"])
    assert len(results) == 5
    for fp, cid, vec in items:
        np.testing.assert_array_equal(results[fp], vec)


def test_idempotent_put_no_index_growth(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    v = _rand_vec(0)
    cache.put("fp1", "c1", v)
    cache.put("fp1", "c1", v)
    cache.put("fp1", "c1", v)
    # Re-puts invalidate the previous entry but the index only tracks one
    # active fingerprint.
    assert cache.stats().valid_entries == 1


# ---------------------------------------------------------------------------
# Invalidation
# ---------------------------------------------------------------------------


def test_invalidate_returns_true_when_existed(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    cache.put("fp1", "c", _rand_vec())
    assert cache.invalidate("fp1") is True
    assert cache.get("fp1") is None


def test_invalidate_returns_false_when_unknown(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    assert cache.invalidate("unknown") is False


def test_invalidate_by_chunk_id_prefix(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    cache.put("fp1", "decisions/ADR-001.md", _rand_vec(1))
    cache.put("fp2", "decisions/ADR-001.md#h2-decision", _rand_vec(2))
    cache.put("fp3", "decisions/ADR-002.md", _rand_vec(3))
    count = cache.invalidate_by_chunk_id("decisions/ADR-001.md")
    assert count == 2
    assert cache.get("fp1") is None
    assert cache.get("fp2") is None
    assert cache.get("fp3") is not None


def test_invalidate_by_chunk_id_idempotent(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    cache.put("fp1", "decisions/ADR-001.md", _rand_vec())
    assert cache.invalidate_by_chunk_id("decisions/ADR-001.md") == 1
    # Second call: already invalidated, returns 0.
    assert cache.invalidate_by_chunk_id("decisions/ADR-001.md") == 0


# ---------------------------------------------------------------------------
# Compact
# ---------------------------------------------------------------------------


def test_compact_reclaims_space(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    for i in range(10):
        cache.put(f"fp{i}", f"c{i}", _rand_vec(i))
    for i in range(5):
        cache.invalidate(f"fp{i}")
    size_before = cache.stats().size_bytes
    cache.compact()
    size_after = cache.stats().size_bytes
    assert size_after < size_before
    # Valid entries remain readable.
    for i in range(5, 10):
        assert cache.get(f"fp{i}") is not None


def test_compact_preserves_vectors_exactly(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    vectors = {f"fp{i}": _rand_vec(i) for i in range(6)}
    for fp, v in vectors.items():
        cache.put(fp, f"c-{fp}", v)
    cache.invalidate("fp0")
    cache.invalidate("fp3")
    cache.compact()
    for fp in ("fp1", "fp2", "fp4", "fp5"):
        out = cache.get(fp)
        np.testing.assert_array_equal(out, vectors[fp])


def test_compact_on_empty_cache_is_safe(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    cache.compact()  # no raise
    assert cache.stats().total_entries == 0


# ---------------------------------------------------------------------------
# Persistence across restart
# ---------------------------------------------------------------------------


def test_persistence_across_restart(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    v = _rand_vec(0)
    cache.put("fp1", "c1", v)
    del cache

    cache2 = VectorCache(tmp_path / "vectors")
    out = cache2.get("fp1")
    np.testing.assert_array_equal(out, v)


def test_corrupt_index_json_resets(tmp_path: Path) -> None:
    cache_dir = tmp_path / "vectors"
    cache_dir.mkdir()
    (cache_dir / "index.json").write_text("not json{{", encoding="utf-8")
    # Should NOT raise; cache resets silently.
    cache = VectorCache(cache_dir)
    assert cache.stats().total_entries == 0


def test_schema_version_mismatch_resets(tmp_path: Path) -> None:
    cache_dir = tmp_path / "vectors"
    cache_dir.mkdir()
    (cache_dir / "index.json").write_text(
        json.dumps(
            {"schema_version": CACHE_SCHEMA_VERSION + 99, "entries": {}, "invalidated": []}
        ),
        encoding="utf-8",
    )
    (cache_dir / "chunks.bin").write_bytes(b"\x00" * 100)
    cache = VectorCache(cache_dir)
    assert cache.stats().total_entries == 0
    # chunks.bin should be removed.
    assert not (cache_dir / "chunks.bin").exists()


def test_malformed_index_entry_resets(tmp_path: Path) -> None:
    cache_dir = tmp_path / "vectors"
    cache_dir.mkdir()
    (cache_dir / "index.json").write_text(
        json.dumps(
            {
                "schema_version": CACHE_SCHEMA_VERSION,
                "entries": {"fp1": {"missing_fields": True}},
                "invalidated": [],
            }
        ),
        encoding="utf-8",
    )
    cache = VectorCache(cache_dir)
    assert cache.stats().total_entries == 0


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


def test_stats_counts_hits_and_misses(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    cache.put("fp1", "c", _rand_vec())
    cache.get("fp1")
    cache.get("fp1")
    cache.get("missing")
    s = cache.stats()
    assert s.hit_count == 2
    assert s.miss_count == 1
    assert s.hit_rate == 2 / 3


def test_stats_invalidated_counter(tmp_path: Path) -> None:
    # ``auto_compact=False`` keeps the invalidated entries around so the
    # counter is observable (otherwise auto-compaction at 30% would reclaim
    # them before stats() is called).
    cache = VectorCache(tmp_path / "vectors", auto_compact=False)
    for i in range(4):
        cache.put(f"fp{i}", f"c{i}", _rand_vec(i))
    cache.invalidate("fp0")
    cache.invalidate("fp1")
    s = cache.stats()
    assert s.total_entries == 4
    assert s.invalidated_entries == 2
    assert s.valid_entries == 2


def test_cache_stats_hit_rate_zero_when_no_calls() -> None:
    s = CacheStats()
    assert s.hit_rate == 0.0


# ---------------------------------------------------------------------------
# Vector validation
# ---------------------------------------------------------------------------


def test_put_invalid_dimension_raises(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    bad = np.random.rand(100).astype(np.float32)
    with pytest.raises(ValueError, match="384"):
        cache.put("fp", "c", bad)


def test_put_coerces_float64_to_float32(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    vec_f64 = np.random.rand(VECTOR_DIM).astype(np.float64)
    cache.put("fp", "c", vec_f64)
    out = cache.get("fp")
    assert out.dtype == np.float32


# ---------------------------------------------------------------------------
# Clear / containment
# ---------------------------------------------------------------------------


def test_clear_removes_everything(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    for i in range(3):
        cache.put(f"fp{i}", f"c{i}", _rand_vec(i))
    cache.clear()
    s = cache.stats()
    assert s.total_entries == 0
    assert s.size_bytes == 0


def test_contains_returns_true_for_valid_entries(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    cache.put("fp1", "c", _rand_vec())
    assert "fp1" in cache
    cache.invalidate("fp1")
    assert "fp1" not in cache


def test_len_excludes_invalidated(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    cache.put("fp1", "c1", _rand_vec(1))
    cache.put("fp2", "c2", _rand_vec(2))
    assert len(cache) == 2
    cache.invalidate("fp1")
    assert len(cache) == 1


# ---------------------------------------------------------------------------
# Concurrency (single process)
# ---------------------------------------------------------------------------


def test_concurrent_puts_dont_corrupt_index(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")

    def worker(idx: int) -> None:
        cache.put(f"fp{idx}", f"c{idx}", _rand_vec(idx))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # All 20 fingerprints landed.
    assert cache.stats().total_entries == 20
    # Re-open and verify.
    cache2 = VectorCache(tmp_path / "vectors")
    assert cache2.stats().total_entries == 20
