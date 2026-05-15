"""Unit tests for ContextPresenter legacy paths (Item #2 deuda residual).

Covers branches in ``to_markdown`` and ``to_compact`` that were previously
exercised only via integration tests. Target: presenter.py >= 90%
coverage, with to_markdown / to_compact branches >= 95%.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from cortex.context_enricher.presenter import ContextPresenter
from cortex.models import EnrichedContext, EnrichedItem, WorkContext


def _work() -> WorkContext:
    return WorkContext(source="manual", changed_files=[], keywords=[], search_queries=[])


def _item(**overrides: object) -> EnrichedItem:
    base: dict[str, object] = dict(
        source="episodic",
        source_id="mem_1",
        title="Item title",
        content="Sample body",
        score=0.5,
        enriched_score=0.6,
        matched_by=["topic_search"],
        files_mentioned=[],
        tags=[],
    )
    base.update(overrides)
    return EnrichedItem(**base)  # type: ignore[arg-type]


def _ctx(items: list[EnrichedItem]) -> EnrichedContext:
    return EnrichedContext(
        work=_work(),
        items=items,
        total_searches=1,
        total_raw_hits=len(items),
        total_items=len(items),
        total_chars=sum(len(i.content) for i in items),
        within_budget=True,
    )


# ---------------------------------------------------------------------------
# to_markdown
# ---------------------------------------------------------------------------


class TestToMarkdown:
    def test_empty_items_returns_no_memories_header(self) -> None:
        ctx = _ctx([])
        out = ContextPresenter.to_markdown(ctx)
        assert "No related memories found" in out
        assert "new area of the codebase" in out

    def test_renders_metadata_line_with_date_files_tags(self) -> None:
        item = _item(
            date=datetime(2026, 1, 15, tzinfo=UTC),
            files_mentioned=["cortex/handoff.py"],
            tags=["release"],
        )
        out = ContextPresenter.to_markdown(_ctx([item]))
        assert "2026-01-15" in out
        assert "cortex/handoff.py" in out
        assert "`release`" in out

    def test_truncates_long_content_with_ellipsis(self) -> None:
        long = "x" * 300
        item = _item(content=long)
        out = ContextPresenter.to_markdown(_ctx([item]))
        assert "…" in out
        assert "x" * 200 in out
        assert "x" * 201 not in out

    def test_semantic_item_renders_semantic_tag(self) -> None:
        item = _item(source="semantic", source_id="vault/specs/x.md")
        out = ContextPresenter.to_markdown(_ctx([item]))
        assert "[SEMANTIC]" in out
        assert "📖" in out

    def test_matched_by_strategies_render_label(self) -> None:
        item = _item(matched_by=["topic_search", "keyword_query"])
        out = ContextPresenter.to_markdown(_ctx([item]))
        assert "Matched by: topic, keyword" in out

    def test_footer_with_expand_hint(self) -> None:
        out = ContextPresenter.to_markdown(_ctx([_item()]))
        assert "cortex context --expand" in out


# ---------------------------------------------------------------------------
# to_compact
# ---------------------------------------------------------------------------


class TestToCompact:
    def test_empty_items_returns_header(self) -> None:
        out = ContextPresenter.to_compact(_ctx([]))
        assert "No related memories found" in out

    def test_renders_one_block_per_item(self) -> None:
        items = [_item(title="A"), _item(title="B")]
        out = ContextPresenter.to_compact(_ctx(items))
        assert "### A" in out
        assert "### B" in out

    def test_handles_unicode_and_strips_newlines(self) -> None:
        item = _item(content="línea uno\nlínea dos\nδéltα")
        out = ContextPresenter.to_compact(_ctx([item]))
        assert "δéltα" in out
        # Body line should join the multi-line content with spaces.
        assert "línea uno línea dos δéltα" in out

    def test_meta_line_combines_files_date_strategies(self) -> None:
        item = _item(
            files_mentioned=["a.py", "b.py"],
            date=datetime(2026, 5, 15, tzinfo=UTC),
            matched_by=["topic_search"],
        )
        out = ContextPresenter.to_compact(_ctx([item]))
        assert "Files: a.py, b.py" in out
        assert "2026-05-15" in out
        assert "Matched by: topic" in out


# ---------------------------------------------------------------------------
# to_markdown_grouped / to_compact_grouped
# ---------------------------------------------------------------------------


class TestGroupedFormatters:
    def test_grouped_empty_items(self) -> None:
        out = ContextPresenter.to_markdown_grouped(_ctx([]))
        assert "No related memories found" in out

    def test_grouped_groups_by_doc_type_descending_by_score(self) -> None:
        a = _item(title="Spec A", doc_type="spec", enriched_score=0.4)
        b = _item(title="ADR-007", doc_type="adr", enriched_score=0.9)
        out = ContextPresenter.to_markdown_grouped(_ctx([a, b]))
        # ADR group with higher score must appear before SPEC.
        assert out.index("## ADR") < out.index("## SPEC")

    def test_grouped_renders_section_title_and_scope(self) -> None:
        item = _item(
            doc_type="runbook",
            matched_section_title="Rollback",
            vault_scope="enterprise",
            enriched_score=0.8,
        )
        out = ContextPresenter.to_markdown_grouped(_ctx([item]))
        assert "section: Rollback" in out
        assert "scope: enterprise" in out

    def test_grouped_truncates_long_content(self) -> None:
        item = _item(content="z" * 300, doc_type="spec", enriched_score=0.8)
        out = ContextPresenter.to_markdown_grouped(_ctx([item]))
        assert "…" in out

    def test_other_label_for_items_without_doc_type(self) -> None:
        item = _item(doc_type=None, enriched_score=0.5)
        out = ContextPresenter.to_markdown_grouped(_ctx([item]))
        assert "## OTHER" in out

    def test_compact_grouped_empty(self) -> None:
        out = ContextPresenter.to_compact_grouped(_ctx([]))
        assert "No related memories found" in out

    def test_compact_grouped_renders_doc_type_uppercase_block(self) -> None:
        item = _item(doc_type="spec", enriched_score=0.7)
        out = ContextPresenter.to_compact_grouped(_ctx([item]))
        assert "[SPEC]" in out


# ---------------------------------------------------------------------------
# to_json
# ---------------------------------------------------------------------------


class TestToJson:
    def test_to_json_emits_valid_payload(self) -> None:
        item = _item(date=datetime(2026, 5, 15, tzinfo=UTC), doc_type="spec")
        out = ContextPresenter.to_json(_ctx([item]))
        payload = json.loads(out)
        assert payload["has_context"] is True
        assert payload["total_items"] == 1
        assert payload["items"][0]["doc_type"] == "spec"
        assert payload["items"][0]["date"] == "2026-05-15T00:00:00+00:00"

    def test_to_json_empty_context_has_no_items(self) -> None:
        payload = json.loads(ContextPresenter.to_json(_ctx([])))
        assert payload["has_context"] is False
        assert payload["items"] == []
