"""Tests for VaultReader integrated with VectorCache (Fase 06)."""

from __future__ import annotations

from pathlib import Path

import pytest

from cortex.semantic.vault_reader import VaultReader
from cortex.semantic.vector_cache import VectorCache


def _seed_vault(vault: Path, count: int = 3) -> None:
    vault.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (vault / f"note{i}.md").write_text(
            f"---\ntitle: Note {i}\n---\nContent of note {i} with some words.",
            encoding="utf-8",
        )


def test_sync_uses_cache_on_second_run(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _seed_vault(vault, count=3)
    cache = VectorCache(tmp_path / ".cortex" / "vectors")

    r1 = VaultReader(str(vault), vector_cache=cache)
    r1.sync()
    s1 = cache.stats()
    assert s1.miss_count == 3
    assert s1.hit_count == 0
    assert s1.valid_entries == 3

    # Second VaultReader using the same cache should hit on every entry.
    r2 = VaultReader(str(vault), vector_cache=cache)
    r2.sync()
    s2 = cache.stats()
    assert s2.hit_count == 3  # 3 cache hits on the second sync
    assert s2.miss_count == 3  # the original misses are preserved


def test_sync_without_cache_works_as_before(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _seed_vault(vault, count=2)
    r = VaultReader(str(vault))  # no cache
    r.sync()
    assert r._vector_cache is None
    assert len(r._embeddings) == 2


def test_index_file_uses_cache(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _seed_vault(vault, count=1)
    cache = VectorCache(tmp_path / ".cortex" / "vectors")
    r = VaultReader(str(vault), vector_cache=cache)
    r.sync()
    s_before = cache.stats()

    # Re-indexing the same file should hit the cache.
    r.index_file("note0.md")
    s_after = cache.stats()
    assert s_after.hit_count > s_before.hit_count


def test_modified_content_misses_cache(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _seed_vault(vault, count=1)
    cache = VectorCache(tmp_path / ".cortex" / "vectors")
    r = VaultReader(str(vault), vector_cache=cache)
    r.sync()
    misses_before = cache.stats().miss_count

    # Modify the file: new content -> new fingerprint -> cache miss.
    (vault / "note0.md").write_text(
        "---\ntitle: Note 0\n---\nCompletely different content.",
        encoding="utf-8",
    )
    r.index_file("note0.md")
    misses_after = cache.stats().miss_count
    assert misses_after == misses_before + 1


def test_create_note_populates_cache(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    cache = VectorCache(tmp_path / ".cortex" / "vectors")
    r = VaultReader(str(vault), vector_cache=cache)
    r.create_note(title="New", content="Body of new note")
    assert cache.stats().valid_entries >= 1


def test_search_results_unchanged_with_cache(tmp_path: Path) -> None:
    """A search query produces the same top-k regardless of cache state."""
    vault = tmp_path / "vault"
    _seed_vault(vault, count=3)
    cache = VectorCache(tmp_path / ".cortex" / "vectors")

    r1 = VaultReader(str(vault))  # uncached run
    r1.sync()
    res1 = [d.path for d in r1.search("Note 1", top_k=3)]

    r2 = VaultReader(str(vault), vector_cache=cache)
    r2.sync()
    res2 = [d.path for d in r2.search("Note 1", top_k=3)]

    r3 = VaultReader(str(vault), vector_cache=cache)
    r3.sync()
    res3 = [d.path for d in r3.search("Note 1", top_k=3)]

    assert res1 == res2 == res3
