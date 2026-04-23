"""Shared pytest fixtures for cortex tests."""
from __future__ import annotations

import hashlib
import math
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Embedder helpers — bag-of-words deterministic vectors
# ---------------------------------------------------------------------------

# Each word maps to a fixed position in the vector space.
# We use a hash of the word to pick which dimensions are "active",
# so semantically similar texts (sharing words) get similar vectors.

_DIM = 384
_ACTIVE_DIMS = 50  # how many dimensions each word activates


def _word_vector(word: str) -> list[float]:
    """
    Produce a deterministic vector for a single word.
    Uses the word's hash to select which dimensions are active.
    """
    vec = [0.0] * _DIM
    h = int(hashlib.md5(word.encode()).hexdigest(), 16)
    for i in range(_ACTIVE_DIMS):
        idx = (h >> (i * 7)) % _DIM
        vec[idx] += 1.0
    # Normalize
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def _make_vector(text: str) -> list[float]:
    """
    Bag-of-words embedding: average of word vectors.
    Texts sharing words will have higher cosine similarity.
    """
    words = text.lower().strip().split()
    if not words:
        return [1.0 / math.sqrt(_DIM)] * _DIM  # uniform default

    vec = [0.0] * _DIM
    for w in words:
        wv = _word_vector(w)
        for i in range(_DIM):
            vec[i] += wv[i]

    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


class MockEmbedder:
    """
    Embedder mock using bag-of-words vectors.
    Texts sharing words get higher cosine similarity — enabling
    meaningful search tests without real ML models.
    """

    def embed(self, text: str) -> list[float]:
        return _make_vector(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [_make_vector(t) for t in texts]


# ---------------------------------------------------------------------------
# EpisodicMemoryStore
# ---------------------------------------------------------------------------

@pytest.fixture
def episodic_store(tmp_path):
    """Real EpisodicMemoryStore with mocked Embedder and tmp ChromaDB dir."""
    with patch("cortex.episodic.memory_store.Embedder", return_value=MockEmbedder()):
        from cortex.episodic.memory_store import EpisodicMemoryStore
        return EpisodicMemoryStore(
            persist_dir=str(tmp_path / "chroma"),
            collection_name="test_collection",
        )


# ---------------------------------------------------------------------------
# VaultReader
# ---------------------------------------------------------------------------

@pytest.fixture
def vault_reader(tmp_path):
    """Real VaultReader with mocked Embedder and tmp vault dir."""
    (tmp_path / "auth.md").write_text(
        "---\ntitle: Auth\ntags: [auth]\n---\n\nLogin and refresh token middleware.\n"
    )
    (tmp_path / "api.md").write_text(
        "---\ntitle: API Reference\ntags: [api]\n---\n\nREST API endpoints.\n"
    )
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "payments.md").write_text("# Payments\n\nStripe integration.\n")

    with patch("cortex.semantic.vault_reader.Embedder", return_value=MockEmbedder()):
        from cortex.semantic.vault_reader import VaultReader
        vr = VaultReader(vault_path=str(tmp_path))
        vr.sync()
        return vr


# ---------------------------------------------------------------------------
# MarkdownParser
# ---------------------------------------------------------------------------

@pytest.fixture
def markdown_parser():
    from cortex.semantic.markdown_parser import MarkdownParser
    return MarkdownParser()


# ---------------------------------------------------------------------------
# HybridSearch (with mock stores)
# ---------------------------------------------------------------------------

@pytest.fixture
def hybrid_search_mocks():
    """Return mock episodic store and semantic reader for HybridSearch tests."""
    from cortex.models import EpisodicHit, MemoryEntry, SemanticDocument
    from cortex.retrieval.hybrid_search import HybridSearch

    mock_episodic = MagicMock()
    mock_episodic.search.return_value = [
        EpisodicHit(
            entry=MemoryEntry(id="mem_001", content="Fixed login bug", memory_type="bugfix"),
            score=0.9,
        ),
        EpisodicHit(
            entry=MemoryEntry(id="mem_002", content="Added auth tests", memory_type="testing"),
            score=0.7,
        ),
    ]

    mock_semantic = MagicMock()
    mock_semantic.search.return_value = [
        SemanticDocument(path="auth.md", title="Auth", content="Login flow docs.", score=0.8),
    ]

    hybrid = HybridSearch(
        episodic=mock_episodic,
        semantic=mock_semantic,
        top_k=5,
    )

    return hybrid, mock_episodic, mock_semantic
