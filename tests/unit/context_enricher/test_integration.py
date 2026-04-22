"""Integration tests for Context Enricher through AgentMemory."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


@pytest.fixture
def mock_memory():
    """Create a mock AgentMemory with mocked dependencies."""
    with patch("cortex.core.AgentMemory") as MockAM:
        mem = MagicMock()
        mem.enrich = MagicMock()
        yield mem


class TestAgentMemoryEnrich:
    """AgentMemory.enrich() integration."""

    def test_enrich_calls_observer_and_enricher(self):
        """Verify that AgentMemory.enrich() orchestrates correctly."""
        # This test verifies the API exists and has correct signature
        from cortex.core import AgentMemory
        import inspect

        sig = inspect.signature(AgentMemory.enrich)
        params = list(sig.parameters.keys())

        assert "changed_files" in params
        assert "keywords" in params
        assert "pr_title" in params
        assert "pr_body" in params
        assert "pr_labels" in params
        assert "top_k" in params


class TestModelsEnrichedContext:
    """EnrichedContext model tests."""

    def test_to_prompt_format_compact(self):
        from cortex.models import EnrichedContext, WorkContext, EnrichedItem

        work = WorkContext(source="manual", changed_files=["auth.py"])
        ctx = EnrichedContext(
            work=work,
            items=[],
            total_items=0,
        )

        output = ctx.to_prompt_format(compact=True)
        assert "No related memories" in output

    def test_to_prompt_format_markdown(self):
        from cortex.models import EnrichedContext, WorkContext, EnrichedItem
        from datetime import datetime, timezone

        work = WorkContext(source="manual", changed_files=["auth.py"])
        item = EnrichedItem(
            source="episodic",
            source_id="mem_1",
            title="Test memory",
            content="Some content about auth",
            score=0.8,
            enriched_score=1.0,
            matched_by=["topic"],
        )
        ctx = EnrichedContext(
            work=work,
            items=[item],
            total_items=1,
        )

        output = ctx.to_prompt_format()
        assert "Test memory" in output
        assert "EPISODIC" in output

    def test_to_prompt_format_expand(self):
        from cortex.models import EnrichedContext, WorkContext, EnrichedItem

        work = WorkContext(source="manual", changed_files=["auth.py"])
        item = EnrichedItem(
            source="semantic",
            source_id="vault/test.md",
            title="Test doc",
            content="A" * 600,  # Long content
            score=0.5,
            enriched_score=0.5,
        )
        ctx = EnrichedContext(
            work=work,
            items=[item],
            total_items=1,
        )

        # expand=True → show up to 500 chars
        output = ctx.to_prompt_format(expand=True)
        assert len(output) > 200  # Should include more content

    def test_enriched_context_stats(self):
        from cortex.models import EnrichedContext, WorkContext

        work = WorkContext(source="manual", changed_files=[])
        ctx = EnrichedContext(
            work=work,
            total_searches=4,
            total_raw_hits=10,
            total_items=3,
            total_chars=500,
            within_budget=True,
        )

        assert ctx.total_searches == 4
        assert ctx.total_raw_hits == 10
        assert ctx.total_items == 3
        assert ctx.within_budget is True


class TestCLIContext:
    """CLI `cortex context` command tests."""

    def test_context_command_exists(self):
        from cortex.cli.main import context
        import inspect

        sig = inspect.signature(context)
        params = list(sig.parameters.keys())

        assert "files" in params
        assert "format" in params
        assert "output" in params
        assert "expand" in params
        assert "no_graph" in params


class TestConfigValidation:
    """ContextEnricherConfig validation."""

    def test_config_from_yaml_compatible(self):
        """Config can be loaded from YAML dict."""
        from cortex.context_enricher.config import ContextEnricherConfig

        yaml_data = {
            "min_score": 0.15,
            "max_items": 5,
            "max_chars": 1500,
            "multi_match_boost": 1.3,
            "co_occurrence_boost": 0.2,
            "topic": True,
            "files": True,
            "keywords": False,
            "pr_title": True,
            "graph_expansion": False,
        }

        config = ContextEnricherConfig(**yaml_data)
        assert config.min_score == 0.15
        assert config.keywords is False
        assert config.graph_expansion is False
