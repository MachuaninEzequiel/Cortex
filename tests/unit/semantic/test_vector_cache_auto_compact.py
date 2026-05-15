"""Auto-compaction trigger (Item #3 PLAN-DEUDA-RESIDUAL)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from cortex.semantic.vector_cache import VECTOR_DIM, VectorCache


def _rand_vec(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.random(VECTOR_DIM).astype(np.float32)


def _seed(cache: VectorCache, count: int) -> list[str]:
    fps: list[str] = []
    for i in range(count):
        fp = f"fp-{i}"
        cache.put(fp, f"chunk-{i}", _rand_vec(i))
        fps.append(fp)
    return fps


def test_auto_compact_triggers_at_threshold(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors", auto_compact_threshold=0.30)
    fps = _seed(cache, 10)
    # Invalidating 3 of 10 (30%) should trigger compaction.
    with patch.object(cache, "compact", wraps=cache.compact) as spy:
        for fp in fps[:3]:
            cache.invalidate(fp)
        spy.assert_called_once()


def test_auto_compact_does_not_trigger_below_threshold(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors", auto_compact_threshold=0.30)
    fps = _seed(cache, 10)
    with patch.object(cache, "compact", wraps=cache.compact) as spy:
        for fp in fps[:2]:
            cache.invalidate(fp)
        spy.assert_not_called()


def test_auto_compact_opt_out_disables_trigger(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors", auto_compact=False)
    fps = _seed(cache, 10)
    with patch.object(cache, "compact", wraps=cache.compact) as spy:
        for fp in fps:
            cache.invalidate(fp)
        spy.assert_not_called()


def test_invalid_threshold_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        VectorCache(tmp_path / "vectors", auto_compact_threshold=0.0)
    with pytest.raises(ValueError):
        VectorCache(tmp_path / "vectors", auto_compact_threshold=1.5)


def test_auto_compact_clears_invalidated_after_run(tmp_path: Path) -> None:
    cache = VectorCache(tmp_path / "vectors", auto_compact_threshold=0.30)
    fps = _seed(cache, 10)
    for fp in fps[:3]:
        cache.invalidate(fp)
    stats = cache.stats()
    assert stats.invalidated_entries == 0
    assert stats.valid_entries == 7
