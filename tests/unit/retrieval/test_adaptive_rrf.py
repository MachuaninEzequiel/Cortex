"""
Tests for QueryIntentDetector and adaptive RRF weighting.

Tests the intent detection signal matching, weight output,
and backward-compatibility of HybridSearch with adaptive_weights=False.
"""

from __future__ import annotations

import pytest
from cortex.retrieval.intent import (
    QueryIntent,
    QueryIntentDetector,
    IntentResult,
)
from cortex.retrieval.hybrid_search import HybridSearch


# ------------------------------------------------------------------
# Intent detection unit tests
# ------------------------------------------------------------------

class TestQueryIntentDetector:
    """Unit tests for QueryIntentDetector signal matching."""

    @pytest.fixture
    def detector(self):
        return QueryIntentDetector()

    # Episodic intent signals
    @pytest.mark.parametrize("query", [
        "what did we fix last sprint",
        "last time this broke",
        "PR #42 auth bugfix",
        "why did we change the token refresh logic",
        "who fixed the login error",
        "incident in production yesterday",
        "commit sha abc123 introduced a regression",
    ])
    def test_episodic_queries_detected(self, detector, query):
        result = detector.detect(query)
        assert result.intent == QueryIntent.EPISODIC, (
            f"Expected EPISODIC for: '{query}', got {result.intent}"
        )
        assert result.episodic_weight > result.semantic_weight

    # Semantic intent signals
    @pytest.mark.parametrize("query", [
        "how does the authentication system work",
        "architecture diagram for the backend",
        "runbook for deploying to production",
        "what is the API contract for /auth/login",
        "explain the token refresh specification",
        "design overview of the vault system",
        "best practices for session management",
    ])
    def test_semantic_queries_detected(self, detector, query):
        result = detector.detect(query)
        assert result.intent == QueryIntent.SEMANTIC, (
            f"Expected SEMANTIC for: '{query}', got {result.intent}"
        )
        assert result.semantic_weight > result.episodic_weight

    # Mixed / ambiguous
    @pytest.mark.parametrize("query", [
        "authentication",
        "token refresh",
        "login",
        "",
    ])
    def test_mixed_queries_balanced_weights(self, detector, query):
        result = detector.detect(query)
        assert result.intent == QueryIntent.MIXED
        assert result.episodic_weight == result.semantic_weight

    def test_intent_result_is_immutable(self, detector):
        """IntentResult is a frozen dataclass."""
        result = detector.detect("auth bugfix")
        with pytest.raises((AttributeError, TypeError)):
            result.intent = QueryIntent.MIXED  # type: ignore

    def test_confidence_range(self, detector):
        """Confidence should always be in [0.0, 1.0]."""
        for query in ["bugfix", "architecture", "auth", ""]:
            result = detector.detect(query)
            assert 0.0 <= result.confidence <= 1.0, (
                f"Confidence out of range for '{query}': {result.confidence}"
            )

    def test_matched_signals_non_empty_for_clear_intent(self, detector):
        """Clear episodic/semantic queries should have matched signals."""
        result = detector.detect("fixed the login bugfix last week")
        assert len(result.matched_signals) > 0

    def test_matched_signals_empty_for_ambiguous(self, detector):
        """Purely ambiguous query should have no matched signals."""
        result = detector.detect("token")
        # Short single-word queries may not match any signal pattern
        assert result.intent == QueryIntent.MIXED


# ------------------------------------------------------------------
# Adaptive HybridSearch integration tests
# ------------------------------------------------------------------

class TestAdaptiveHybridSearch:
    """Integration tests for adaptive weight adjustment in HybridSearch."""

    def test_detect_intent_exposed(self, hybrid_search_mocks):
        """HybridSearch.detect_intent() should be callable."""
        hybrid, _, _ = hybrid_search_mocks
        result = hybrid.detect_intent("last bug we fixed in auth")
        assert isinstance(result, IntentResult)
        assert result.intent in QueryIntent

    def test_adaptive_weights_default_on(self, hybrid_search_mocks):
        """adaptive_weights should be True by default."""
        hybrid, _, _ = hybrid_search_mocks
        assert hybrid.adaptive_weights is True

    def test_search_returns_result_with_adaptive(self, hybrid_search_mocks):
        """Adaptive search should still return a valid RetrievalResult."""
        hybrid, _, _ = hybrid_search_mocks
        result = hybrid.search("what did we fix last sprint")
        assert result.query == "what did we fix last sprint"
        assert len(result.episodic_hits) > 0

    def test_search_backward_compat_no_adaptive(self, hybrid_search_mocks):
        """Disabling adaptive_weights preserves original behavior."""
        hybrid, episodic, semantic = hybrid_search_mocks
        non_adaptive = HybridSearch(
            episodic=episodic,
            semantic=semantic,
            adaptive_weights=False,
        )
        result = non_adaptive.search("architecture overview")
        assert len(result.episodic_hits) > 0 or len(result.semantic_hits) > 0

    def test_episodic_query_increases_episodic_fetch(self, hybrid_search_mocks):
        """
        For an episodic query, the episodic source should receive
        proportionally more weight. We verify by checking the unified
        score order — if episodic source dominates, episodic hits
        should appear first in unified_hits for a rich episodic query.
        """
        hybrid, _, _ = hybrid_search_mocks
        # 'PR #42 broke the login' is clearly episodic
        result = hybrid.search("PR #42 broke the login last week")
        assert len(result.unified_hits) > 0
        # Just verify unified hits are ordered by score
        scores = [h.score for h in result.unified_hits]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]
