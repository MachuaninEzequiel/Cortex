"""Regression tests: A2 — silent failure in _embed_batch_with_cache.

Spec: docs/transformacion/04-VECTORIZACION-E-IDIOMA.md Fase A.
A cache write failure mid-batch must NEVER yield empty vectors / empty
search results. Fail-fast on embedder errors; degrade to no-cache (with a
WARNING) on cache-write errors.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from cortex.semantic.vault_reader import VaultReader
from cortex.semantic.vector_cache import VectorCache


_DIM = 8


class FakeEmbedder:
    """Deterministic offline embedder (no model download)."""

    model_name = "fake-model"

    def __init__(self, fail_at: int | None = None) -> None:
        self.fail_at = fail_at  # index within the batch where embed blows up

    def _vec(self, text: str) -> list[float]:
        h = abs(hash(text)) % 1000
        v = [((h + i) % 7 + 1) / 10 for i in range(_DIM)]
        return v

    def embed(self, text: str) -> list[float]:
        return self._vec(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        out = []
        for i, t in enumerate(texts):
            if self.fail_at is not None and i == self.fail_at:
                raise RuntimeError(f"simulated embedder crash at item {i}")
            out.append(self._vec(t))
        return out


class BrokenPutCache:
    """Cache whose writes always fail; reads always miss."""

    def get(self, fingerprint: str):
        return None

    def put(self, fingerprint: str, chunk_id: str, vector) -> None:
        raise OSError("simulated disk full")

    def batch_put(self, items) -> None:
        raise OSError("simulated disk full")


def _seed_vault(vault: Path, count: int) -> None:
    vault.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (vault / f"note{i}.md").write_text(
            f"---\ntitle: Note {i}\ntags: [t]\n---\nBody of note {i} "
            f"with several searchable words about topic {i}.",
            encoding="utf-8",
        )


def test_cache_put_failure_still_indexes_and_searches(tmp_path, caplog):
    """Cache put failing must degrade to no-cache, never to empty results."""
    vault = tmp_path / "vault"
    _seed_vault(vault, 3)
    r = VaultReader(str(vault), vector_cache=BrokenPutCache())
    r._embedder = FakeEmbedder()

    with caplog.at_level(logging.WARNING, logger="cortex.semantic.vault_reader"):
        n = r.sync()

    assert n == 3
    # No incomplete vectors: every chunk has a real vector.
    assert len(r._embeddings) == 3
    assert all(len(v) == _DIM for v in r._embeddings.values())
    # Cache was dropped after the failure (degrade to direct embedding).
    assert r._vector_cache is None
    assert any("cache" in rec.message.lower() for rec in caplog.records)

    hits = r.search("topic 1", top_k=3)
    assert len(hits) == 3


def test_cache_batch_put_failure_midway_keeps_all_vectors(tmp_path):
    vault = tmp_path / "vault"
    _seed_vault(vault, 5)
    cache = VectorCache(tmp_path / "vectors")
    r = VaultReader(str(vault), vector_cache=cache)
    r._embedder = FakeEmbedder()
    r.sync()

    class HalfBroken:
        def get(self, fp):
            return None

        def get_chunk_fingerprints(self, parent_path):
            return {}

        def batch_put(self, items):
            raise OSError("boom")

    r._vector_cache = HalfBroken()
    r.index_file("note0.md")
    vecs = [r._embeddings[cid] for cid in r._embeddings if cid.startswith("note0")]
    assert vecs and all(len(v) == _DIM for v in vecs)


def test_embedder_failure_propagates_loudly(tmp_path):
    """Embedder crashing at item 3 of N must surface as an exception."""
    vault = tmp_path / "vault"
    _seed_vault(vault, 6)
    r = VaultReader(str(vault))
    r._embedder = FakeEmbedder(fail_at=2)

    with pytest.raises(RuntimeError, match="note"):
        r.sync()
