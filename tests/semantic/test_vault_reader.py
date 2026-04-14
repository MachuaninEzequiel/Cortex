"""Tests for VaultReader."""

import pytest
from pathlib import Path


def test_sync_counts_documents(vault_reader):
    count = vault_reader.count()
    assert count == 3


def test_search_finds_relevant(vault_reader):
    results = vault_reader.search("auth login")
    assert len(results) >= 1
    assert any("Auth" in r.title for r in results)


def test_search_quality_related_vs_unrelated(vault_reader):
    """
    With vector embeddings, search always returns results.
    The key property: a related query should score higher on the relevant doc
    than an unrelated query does.
    """
    # "auth login" should score higher on the Auth doc than a nonsense query
    auth_related = vault_reader.search("auth login middleware")
    auth_unrelated = vault_reader.search("zxqyabcdefxyz")

    # Find the Auth doc score in both results
    def get_score(results, title):
        for d in results:
            if title in d.title:
                return d.score
        return 0.0

    auth_score_related = get_score(auth_related, "Auth")
    auth_score_unrelated = get_score(auth_unrelated, "Auth")

    assert auth_score_related > auth_score_unrelated, (
        f"Related query scored Auth at {auth_score_related}, "
        f"unrelated at {auth_score_unrelated}"
    )


def test_create_note(vault_reader, tmp_path):
    path = vault_reader.create_note("New Feature", "Content here.", tags=["feature"])
    assert path.exists()
    assert vault_reader.count() == 4


def test_update_note(vault_reader):
    ok = vault_reader.update_note("auth.md", "# Auth\n\nUpdated content.\n")
    assert ok is True
    doc = vault_reader.get("auth.md")
    assert doc is not None
    assert "Updated content" in doc.content


def test_get_nonexistent(vault_reader):
    doc = vault_reader.get("does_not_exist.md")
    assert doc is None


def test_search_returns_scored_results(vault_reader):
    results = vault_reader.search("auth")
    if results:
        # Results should have positive cosine similarity scores
        assert results[0].score > 0


def test_search_respects_top_k(vault_reader):
    results = vault_reader.search("auth", top_k=1)
    assert len(results) <= 1
