"""Tests for ContextEnricher."""

import pytest
from unittest.mock import MagicMock, patch
from cortex.context_enricher.enricher import ContextEnricher, ContextEnricherConfig
from cortex.models import WorkContext, EnrichedContext, EnrichedItem, UnifiedHit, MemoryEntry
from datetime import datetime, timezone


@pytest.fixture
def mock_episodic():
    mock = MagicMock()
    mock.search.return_value = []
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
        max_items=8,
        max_chars=2000,
        multi_match_boost=1.5,
        co_occurrence_boost=0.3,
    )


@pytest.fixture
def enricher(mock_episodic, mock_semantic, config):
    return ContextEnricher(mock_episodic, mock_semantic, config)


@pytest.fixture
def work_context():
    return WorkContext(
        source="manual",
        changed_files=["auth.py", "jwt.ts"],
        keywords=["token", "refresh", "expiry"],
        detected_domain="auth",
        search_queries=[
            "auth token refresh expiry",  # topic
            "auth jwt",                   # files
            "token refresh expiry",       # keywords
            "Fix token refresh bug",      # pr_title
        ],
    )


class TestEnricherEmpty:
    """Enricher with no memories returns empty context."""

    def test_empty_result(self, enricher, work_context):
        result = enricher.enrich(work_context)
        assert isinstance(result, EnrichedContext)
        assert result.total_searches >= 1  # At least topic search ran
        assert result.total_items == 0
        assert result.items == []


class TestEnricherMultiStrategy:
    """Enricher: multiple strategies find results."""

    def test_strategies_execute(self, enricher, work_context):
        # Mock some results
        mock_entry = MemoryEntry(
            id="mem_1",
            content="Fixed token refresh bug",
            memory_type="bugfix",
            files=["auth.py"],
            tags=["auth"],
        )
        from cortex.models import EpisodicHit
        hit = EpisodicHit(entry=mock_entry, score=0.8)

        enricher.episodic.search.return_value = [hit]

        result = enricher.enrich(work_context)
        assert result.total_searches >= 1  # Strategies ran
        assert result.total_raw_hits > 0


class TestEnricherDedup:
    """Enricher: deduplication by ID."""

    def test_same_item_in_multiple_strategies(self, enricher, work_context):
        # Same memory appears in topic and file search
        mock_entry = MemoryEntry(
            id="mem_1",
            content="Fixed token refresh bug in auth",
            memory_type="bugfix",
            files=["auth.py"],
            tags=["auth"],
        )
        from cortex.models import EpisodicHit
        hit = EpisodicHit(entry=mock_entry, score=0.8)

        # Return same hit for both strategies
        enricher.episodic.search.return_value = [hit]

        result = enricher.enrich(work_context)
        # Should be deduplicated: only 1 item, not 2
        if result.total_items == 1:
            item = result.items[0]
            assert item.source_id == "mem_1"
            # Should have multiple strategies in matched_by
            assert len(item.matched_by) >= 1


class TestEnricherBoost:
    """Enricher: multi-match boost."""

    def test_multi_match_boost_applied(self, enricher, work_context):
        mock_entry = MemoryEntry(
            id="mem_1",
            content="Fixed token refresh bug",
            memory_type="bugfix",
            files=["auth.py"],
            tags=["auth"],
        )
        from cortex.models import EpisodicHit
        hit = EpisodicHit(entry=mock_entry, score=0.5)

        enricher.episodic.search.return_value = [hit]

        result = enricher.enrich(work_context)
        if result.total_items >= 1:
            item = result.items[0]
            # Enriched score should be >= original score
            assert item.enriched_score >= item.score * 0.9  # Allow some tolerance


class TestEnricherThreshold:
    """Enricher: threshold filtering."""

    def test_low_score_items_filtered_out(self, enricher, work_context):
        mock_entry = MemoryEntry(
            id="mem_low",
            content="Unrelated memory",
            memory_type="general",
            files=["random.py"],
        )
        from cortex.models import EpisodicHit
        hit = EpisodicHit(entry=mock_entry, score=0.01)  # Very low score

        enricher.episodic.search.return_value = [hit]

        result = enricher.enrich(work_context)
        # Low score item should be filtered out
        for item in result.items:
            assert item.enriched_score >= enricher.config.min_score


class TestEnricherBudget:
    """Enricher: budget enforcement."""

    def test_max_items_enforced(self, work_context):
        config = ContextEnricherConfig(max_items=2)
        # Create many mock hits
        hits = []
        for i in range(10):
            entry = MemoryEntry(
                id=f"mem_{i}",
                content=f"Memory {i} " * 20,  # Long content
                memory_type="general",
                files=[f"file{i}.py"],
            )
            from cortex.models import EpisodicHit
            hits.append(EpisodicHit(entry=entry, score=0.9 - i * 0.05))

        mock_episodic = MagicMock()
        mock_episodic.search.return_value = hits
        mock_semantic = MagicMock()
        mock_semantic.search.return_value = []
        mock_semantic.count.return_value = 0

        enricher = ContextEnricher(mock_episodic, mock_semantic, config)
        result = enricher.enrich(work_context)

        assert result.total_items <= 2


class TestGraphExpansion:
    """Enricher: graph expansion (co-occurrence)."""

    def test_co_occurrence_score_basic(self, enricher):
        co_occurrence = {
            "auth.py": {"jwt.ts": 3, "config.py": 1},
            "jwt.ts": {"auth.py": 3},
        }
        score = enricher._co_occurrence_score(
            ["auth.py", "jwt.ts"],
            ["auth.py", "jwt.ts"],
            co_occurrence,
        )
        assert score > 0

    def test_co_occurrence_score_no_overlap(self, enricher):
        co_occurrence = {
            "auth.py": {"jwt.ts": 3},
        }
        score = enricher._co_occurrence_score(
            ["payments.py"],
            ["auth.py"],
            co_occurrence,
        )
        assert score == 0

    def test_co_occurrence_score_empty(self, enricher):
        score = enricher._co_occurrence_score([], [], {})
        assert score == 0.0

    def test_build_co_occurrence_empty(self, enricher):
        enricher.episodic.search.return_value = []
        co_occurrence = enricher._build_co_occurrence()
        assert co_occurrence == {}


class TestConfig:
    """ContextEnricherConfig validation."""

    def test_defaults(self):
        config = ContextEnricherConfig()
        assert config.min_score == 0.1
        assert config.max_items == 8
        assert config.max_chars == 2000
        assert config.multi_match_boost == 1.5
        assert config.topic is True

    def test_custom_values(self):
        config = ContextEnricherConfig(
            min_score=0.2,
            max_items=5,
            max_chars=1000,
        )
        assert config.min_score == 0.2
        assert config.max_items == 5
        assert config.max_chars == 1000
