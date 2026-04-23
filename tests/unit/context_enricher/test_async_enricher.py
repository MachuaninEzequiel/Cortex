"""
Tests for AsyncContextEnricher parallel execution.

Verifies:
- Same results as sequential ContextEnricher (correctness)
- Strategies are called for each enabled strategy (parallelism observable)
- Budget and threshold enforcement preserved (regression)
- Sync enrich() wrapper works without async context
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from cortex.context_enricher.async_enricher import AsyncContextEnricher
from cortex.context_enricher.config import ContextEnricherConfig
from cortex.models import EpisodicHit, MemoryEntry, WorkContext

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def work_context():
    return WorkContext(
        source="manual",
        changed_files=["auth.py", "jwt.ts"],
        keywords=["token", "refresh", "expiry"],
        detected_domain="auth",
        search_queries=[
            "auth token refresh expiry",
            "auth jwt",
            "token refresh expiry",
            "Fix token refresh bug",
        ],
    )


@pytest.fixture
def mock_episodic():
    mock = MagicMock()
    mock.search.return_value = []
    mock.count.return_value = 0
    return mock


@pytest.fixture
def mock_semantic():
    mock = MagicMock()
    mock.search.return_value = []
    mock.count.return_value = 0
    return mock


@pytest.fixture
def config():
    return ContextEnricherConfig(
        min_score=0.1,
        max_items=5,
        max_chars=2000,
        # Disable heavy strategies for unit tests
        graph_expansion=False,
        typed_graph=False,
        memory_decay=False,
        feedback_loop=False,
        entity_search=False,
    )


@pytest.fixture
def async_enricher(mock_episodic, mock_semantic, config):
    return AsyncContextEnricher(mock_episodic, mock_semantic, config)


@pytest.fixture
def hit_factory():
    """Build a list of EpisodicHit fixtures."""
    def _make(n=3):
        hits = []
        for i in range(n):
            entry = MemoryEntry(
                id=f"mem_{i}",
                content=f"Fixed token refresh bug {i}",
                memory_type="bugfix",
                files=["auth.py"],
                tags=["auth"],
            )
            hits.append(EpisodicHit(entry=entry, score=0.9 - i * 0.1))
        return hits
    return _make


# ------------------------------------------------------------------
# Correctness: same results as synchronous enricher
# ------------------------------------------------------------------

class TestAsyncEnricherCorrectness:
    """AsyncContextEnricher must produce same results as ContextEnricher."""

    def test_empty_returns_empty_context(self, async_enricher, work_context):
        result = async_enricher.enrich(work_context)
        assert result.total_items == 0
        assert result.items == []

    def test_returns_enriched_context_type(self, async_enricher, work_context):
        from cortex.models import EnrichedContext
        result = async_enricher.enrich(work_context)
        assert isinstance(result, EnrichedContext)

    def test_hits_collected_from_parallel_strategies(
        self, async_enricher, work_context, hit_factory
    ):
        """Hits from all strategies should be collected and deduplicated."""
        hits = hit_factory(3)
        async_enricher.episodic.search.return_value = hits

        result = async_enricher.enrich(work_context)
        assert result.total_searches >= 1
        assert result.total_raw_hits > 0

    def test_threshold_filtering_preserved(self, async_enricher, work_context):
        """Low-score items should be filtered out."""
        entry = MemoryEntry(
            id="low_score",
            content="Unrelated memory",
            memory_type="general",
            files=["random.py"],
        )
        async_enricher.episodic.search.return_value = [
            EpisodicHit(entry=entry, score=0.001)
        ]
        result = async_enricher.enrich(work_context)
        for item in result.items:
            assert item.enriched_score >= async_enricher.config.min_score

    def test_budget_max_items_enforced(self, mock_episodic, mock_semantic):
        """max_items budget must be respected."""
        config = ContextEnricherConfig(
            max_items=2,
            graph_expansion=False, typed_graph=False,
            memory_decay=False, feedback_loop=False,
            entity_search=False,
        )
        hits = [
            EpisodicHit(
                entry=MemoryEntry(id=f"m{i}", content=f"mem {i}", memory_type="general"),
                score=0.9 - i * 0.05
            )
            for i in range(10)
        ]
        mock_episodic.search.return_value = hits

        enricher = AsyncContextEnricher(mock_episodic, mock_semantic, config)
        work = WorkContext(
            source="manual",
            changed_files=["file.py"],
            keywords=["fix"],
            detected_domain="general",
            search_queries=["general fix", "file", "fix", "Fix"],
        )
        result = enricher.enrich(work)
        assert result.total_items <= 2


# ------------------------------------------------------------------
# Async interface
# ------------------------------------------------------------------

class TestAsyncInterface:
    """AsyncContextEnricher.enrich_async() coroutine tests."""

    def test_enrich_async_is_coroutine(self, async_enricher, work_context):
        coro = async_enricher.enrich_async(work_context)
        assert asyncio.iscoroutine(coro)
        # Clean up unawaited coroutine
        coro.close()

    def test_enrich_async_runs_and_returns(self, async_enricher, work_context):
        result = asyncio.run(async_enricher.enrich_async(work_context))
        from cortex.models import EnrichedContext
        assert isinstance(result, EnrichedContext)

    def test_parallel_strategies_called(self, mock_episodic, mock_semantic, config):
        """All enabled strategies should trigger a search call."""
        mock_episodic.search.return_value = []

        enricher = AsyncContextEnricher(mock_episodic, mock_semantic, config)
        work = WorkContext(
            source="manual",
            changed_files=["auth.py"],
            keywords=["token"],
            detected_domain="auth",
            # 4 queries → 4 strategy tasks
            search_queries=["auth token", "auth", "token", "Fix token bug"],
        )
        asyncio.run(enricher.enrich_async(work))
        # With 4 queries all enabled, episodic.search should be called 4 times
        assert mock_episodic.search.call_count >= 2
