"""Granular cache invalidation (Item #4 PLAN-DEUDA-RESIDUAL)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from cortex.semantic.vector_cache import VECTOR_DIM, VectorCache


def _rand_vec(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.random(VECTOR_DIM).astype(np.float32)


def _seed_doc(cache: VectorCache, parent: str, n: int) -> list[str]:
    chunk_ids = [f"{parent}#h2-section-{i}" for i in range(n)]
    for i, cid in enumerate(chunk_ids):
        cache.put(f"fp-{parent}-{i}", cid, _rand_vec(i))
    return chunk_ids


def test_get_chunk_fingerprints_returns_all_chunks_for_parent(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    _seed_doc(cache, "decisions/ADR-007-foo.md", n=4)
    _seed_doc(cache, "specs/spec-other.md", n=2)

    fps = cache.get_chunk_fingerprints("decisions/ADR-007-foo.md")
    assert len(fps) == 4
    for cid in fps:
        assert cid.startswith("decisions/ADR-007-foo.md#")


def test_get_chunk_fingerprints_returns_empty_when_parent_unknown(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    _seed_doc(cache, "decisions/ADR-007-foo.md", n=2)
    assert cache.get_chunk_fingerprints("missing/doc.md") == {}


def test_get_chunk_fingerprints_ignores_invalidated_entries(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    chunk_ids = _seed_doc(cache, "decisions/ADR-007-foo.md", n=3)

    fps = cache.get_chunk_fingerprints("decisions/ADR-007-foo.md")
    one_fp = next(iter(fps.values()))
    cache.invalidate(one_fp)

    remaining = cache.get_chunk_fingerprints("decisions/ADR-007-foo.md")
    assert len(remaining) == len(chunk_ids) - 1


def test_invalidate_chunks_targets_exact_chunk_ids(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    chunk_ids = _seed_doc(cache, "decisions/ADR-007-foo.md", n=4)

    invalidated = cache.invalidate_chunks([chunk_ids[1], chunk_ids[3]])
    assert invalidated == 2
    remaining = cache.get_chunk_fingerprints("decisions/ADR-007-foo.md")
    assert chunk_ids[0] in remaining
    assert chunk_ids[2] in remaining
    assert chunk_ids[1] not in remaining
    assert chunk_ids[3] not in remaining


def test_invalidate_chunks_is_idempotent(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    chunk_ids = _seed_doc(cache, "decisions/ADR-007-foo.md", n=2)

    first = cache.invalidate_chunks(chunk_ids)
    second = cache.invalidate_chunks(chunk_ids)
    assert first == len(chunk_ids)
    assert second == 0


def test_invalidate_chunks_empty_input_is_noop(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors")
    assert cache.invalidate_chunks([]) == 0
