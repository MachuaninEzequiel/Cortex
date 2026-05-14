"""Cold-start performance check for the vector cache (Fase 06).

Builds a synthetic vault of N notes, syncs twice with the same VectorCache,
and asserts the second sync is materially faster than the first. This guards
against regressions that bypass the cache.

The thresholds are conservative: the goal is to catch ``cache-not-hit``
regressions, not to micro-benchmark embedding latency.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from cortex.semantic.vault_reader import VaultReader
from cortex.semantic.vector_cache import VectorCache


def _seed_vault(vault: Path, count: int) -> None:
    vault.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (vault / f"note{i}.md").write_text(
            f"---\ntitle: Note {i}\n---\nThis is the body of note number {i}.\n"
            f"It mentions topic-{i % 5} and tag-{i % 7}.",
            encoding="utf-8",
        )


@pytest.mark.parametrize("note_count", [30])
def test_warm_sync_is_faster_than_cold(tmp_path: Path, note_count: int) -> None:
    """Second sync (cache warm) is at least 3x faster than the first sync."""
    vault = tmp_path / "vault"
    _seed_vault(vault, count=note_count)
    cache = VectorCache(tmp_path / ".cortex" / "vectors")

    # Cold sync: cache is empty, every doc is embedded.
    t0 = time.perf_counter()
    VaultReader(str(vault), vector_cache=cache).sync()
    cold_seconds = time.perf_counter() - t0

    # Warm sync: same cache, every fingerprint is a hit.
    t1 = time.perf_counter()
    VaultReader(str(vault), vector_cache=cache).sync()
    warm_seconds = time.perf_counter() - t1

    speedup = cold_seconds / max(warm_seconds, 1e-6)
    # We expect the warm path to dominate by at least 3x. CI variance is high
    # so the threshold is conservative; a regression that fully bypasses the
    # cache would push the ratio to ~1.0.
    assert speedup >= 3.0, (
        f"Warm sync should be >= 3x faster than cold "
        f"(got cold={cold_seconds:.3f}s, warm={warm_seconds:.3f}s, "
        f"speedup={speedup:.2f}x)."
    )
    # Hit rate after the warm sync must be at least equal to the doc count
    # (only the warm sync contributes hits).
    stats = cache.stats()
    assert stats.hit_count >= note_count


def test_warm_sync_no_re_embedding(tmp_path: Path) -> None:
    """Second sync hits the cache for every doc."""
    vault = tmp_path / "vault"
    _seed_vault(vault, count=5)
    cache = VectorCache(tmp_path / ".cortex" / "vectors")
    VaultReader(str(vault), vector_cache=cache).sync()
    misses_after_cold = cache.stats().miss_count

    VaultReader(str(vault), vector_cache=cache).sync()
    stats = cache.stats()
    assert stats.miss_count == misses_after_cold  # no new misses
    assert stats.hit_count >= 5
