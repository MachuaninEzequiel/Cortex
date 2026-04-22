"""Tests for HybridSearch."""

import pytest


def test_search_returns_result(hybrid_search_mocks):
    hybrid, _, _ = hybrid_search_mocks
    result = hybrid.search("login bug")
    assert result.query == "login bug"
    assert len(result.episodic_hits) > 0
    assert len(result.semantic_hits) > 0


def test_rrf_reranks_correctly(hybrid_search_mocks):
    hybrid, _, _ = hybrid_search_mocks
    result = hybrid.search("auth")
    # RRF scores should be monotonically decreasing within each source
    hits = result.episodic_hits
    if len(hits) >= 2:
        assert hits[0].score >= hits[1].score


def test_to_prompt_is_string(hybrid_search_mocks):
    hybrid, _, _ = hybrid_search_mocks
    result = hybrid.search("login")
    prompt = result.to_prompt()
    assert isinstance(prompt, str)
    assert "login" in prompt.lower()


def test_top_k_override(hybrid_search_mocks):
    hybrid, _, _ = hybrid_search_mocks
    result = hybrid.search("auth", top_k=1)
    assert len(result.episodic_hits) <= 1
    assert len(result.semantic_hits) <= 1


def test_unified_hits_populated(hybrid_search_mocks):
    """True cross-source RRF should populate unified_hits."""
    hybrid, _, _ = hybrid_search_mocks
    result = hybrid.search("auth")
    assert len(result.unified_hits) > 0
    # Unified list should contain both episodic and semantic entries interleaved
    sources = {h.source for h in result.unified_hits}
    assert "episodic" in sources
    assert "semantic" in sources


def test_unified_scores_monotonic(hybrid_search_mocks):
    """Unified scores should be strictly decreasing."""
    hybrid, _, _ = hybrid_search_mocks
    result = hybrid.search("anything")
    scores = [h.score for h in result.unified_hits]
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i + 1], f"Score at {i} ({scores[i]}) < score at {i+1} ({scores[i+1]})"


def test_unified_hit_display_properties(hybrid_search_mocks):
    """UnifiedHit display properties should work correctly."""
    hybrid, _, _ = hybrid_search_mocks
    result = hybrid.search("login")
    for hit in result.unified_hits:
        assert hit.display_title  # non-empty
        assert isinstance(hit.display_content, str)
        assert isinstance(hit.display_path, str)
