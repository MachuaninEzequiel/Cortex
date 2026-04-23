"""Tests for ContextPresenter."""

import json
from datetime import datetime, timezone

import pytest

from cortex.context_enricher.presenter import ContextPresenter
from cortex.models import EnrichedContext, EnrichedItem, WorkContext


@pytest.fixture
def sample_context():
    work = WorkContext(
        source="manual",
        changed_files=["auth.py"],
        detected_domain="auth",
        domain_confidence=0.8,
        search_queries=["auth token", "auth", "token", "Fix auth"],
    )

    items = [
        EnrichedItem(
            source="episodic",
            source_id="mem_1",
            title="[bugfix] Fixed token refresh",
            content="The token refresh endpoint wasn't validating expiry. "
                    "Fixed by adding timestamp validation in refresh_token().",
            score=0.8,
            enriched_score=1.2,
            matched_by=["topic_search", "file_search"],
            files_mentioned=["auth.py", "jwt.ts"],
            date=datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc),
            tags=["auth", "bugfix"],
        ),
        EnrichedItem(
            source="semantic",
            source_id="vault/decisions/adr_003.md",
            title="ADR-003: Token Refresh Strategy",
            content="Using short-lived access tokens (15min) with rotating refresh tokens. "
                    "Refresh tokens stored as httpOnly cookies.",
            score=0.6,
            enriched_score=0.6,
            matched_by=["topic_search"],
            files_mentioned=[],
            date=None,
            tags=["architecture", "auth"],
        ),
    ]

    return EnrichedContext(
        work=work,
        items=items,
        total_searches=4,
        total_raw_hits=7,
        total_items=2,
        total_chars=350,
        within_budget=True,
    )


class TestPresenterMarkdown:
    """Presenter: markdown format."""

    def test_markdown_output(self, sample_context):
        output = ContextPresenter.to_markdown(sample_context)
        assert "🧠 Cortex Context" in output
        assert "Found 2 related memories" in output
        assert "Fixed token refresh" in output
        assert "ADR-003" in output
        assert "Matched by:" in output

    def test_markdown_empty(self):
        work = WorkContext(source="manual", changed_files=[])
        ctx = EnrichedContext(work=work, items=[])
        output = ContextPresenter.to_markdown(ctx)
        assert "No related memories found" in output

    def test_markdown_has_metadata(self, sample_context):
        output = ContextPresenter.to_markdown(sample_context)
        assert "auth.py" in output  # files mentioned
        assert "EPISODIC" in output
        assert "SEMANTIC" in output


class TestPresenterCompact:
    """Presenter: compact format for LLM prompts."""

    def test_compact_output(self, sample_context):
        output = ContextPresenter.to_compact(sample_context)
        assert "🧠 Cortex Context" in output
        assert "Fixed token refresh" in output
        # Should be shorter than markdown
        markdown = ContextPresenter.to_markdown(sample_context)
        assert len(output) < len(markdown)

    def test_compact_empty(self):
        work = WorkContext(source="manual", changed_files=[])
        ctx = EnrichedContext(work=work, items=[])
        output = ContextPresenter.to_compact(ctx)
        assert "No related memories found" in output


class TestPresenterJSON:
    """Presenter: JSON format for CI/CD."""

    def test_json_output_valid(self, sample_context):
        json_str = ContextPresenter.to_json(sample_context)
        data = json.loads(json_str)
        assert data["has_context"] is True
        assert data["total_items"] == 2
        assert len(data["items"]) == 2

    def test_json_has_work_metadata(self, sample_context):
        json_str = ContextPresenter.to_json(sample_context)
        data = json.loads(json_str)
        assert "work" in data
        assert data["work"]["detected_domain"] == "auth"
        assert data["work"]["changed_files"] == ["auth.py"]

    def test_json_has_item_details(self, sample_context):
        json_str = ContextPresenter.to_json(sample_context)
        data = json.loads(json_str)
        item = data["items"][0]
        assert item["source"] == "episodic"
        assert item["source_id"] == "mem_1"
        assert "auth" in item["tags"]

    def test_json_empty(self):
        work = WorkContext(source="manual", changed_files=[])
        ctx = EnrichedContext(work=work, items=[])
        json_str = ContextPresenter.to_json(ctx)
        data = json.loads(json_str)
        assert data["has_context"] is False
        assert data["total_items"] == 0
