"""Tests for ContextPresenter grouped output (Fase 08)."""

from __future__ import annotations

import pytest

from cortex.context_enricher.presenter import ContextPresenter
from cortex.models import EnrichedContext, EnrichedItem, WorkContext


def _item(source_id: str, *, doc_type: str | None, score: float = 0.5) -> EnrichedItem:
    return EnrichedItem(
        source="semantic", source_id=source_id, title=f"Title {source_id}",
        content=f"body of {source_id} with some content",
        score=score, enriched_score=score, matched_by=["topic_search"],
        doc_type=doc_type,
    )


def _ctx(items: list[EnrichedItem]) -> EnrichedContext:
    return EnrichedContext(
        work=WorkContext(source="manual", changed_files=[], keywords=[], search_queries=[]),
        items=items, total_items=len(items),
        total_chars=sum(len(i.content) for i in items),
    )


def test_grouped_markdown_groups_by_doc_type() -> None:
    ctx = _ctx([
        _item("a", doc_type="adr", score=0.9),
        _item("b", doc_type="runbook", score=0.5),
        _item("c", doc_type="adr", score=0.7),
    ])
    out = ContextPresenter.to_markdown_grouped(ctx)
    assert "## ADR (2 items)" in out
    assert "## RUNBOOK (1 items)" in out


def test_grouped_markdown_orders_by_max_score() -> None:
    """Group with the highest single score appears first."""
    ctx = _ctx([
        _item("a", doc_type="adr", score=0.4),
        _item("b", doc_type="runbook", score=0.9),
    ])
    out = ContextPresenter.to_markdown_grouped(ctx)
    runbook_pos = out.index("RUNBOOK")
    adr_pos = out.index("ADR")
    assert runbook_pos < adr_pos


def test_grouped_markdown_other_for_none_doc_type() -> None:
    ctx = _ctx([
        _item("a", doc_type="adr"),
        _item("legacy", doc_type=None),
    ])
    out = ContextPresenter.to_markdown_grouped(ctx)
    assert "OTHER" in out


def test_grouped_markdown_empty_returns_no_memories() -> None:
    ctx = _ctx([])
    out = ContextPresenter.to_markdown_grouped(ctx)
    assert "No related memories" in out


def test_grouped_compact_groups_by_doc_type() -> None:
    ctx = _ctx([
        _item("a", doc_type="adr", score=0.9),
        _item("b", doc_type="runbook", score=0.5),
    ])
    out = ContextPresenter.to_compact_grouped(ctx)
    assert "[ADR]" in out
    assert "[RUNBOOK]" in out


def test_grouped_compact_empty() -> None:
    ctx = _ctx([])
    out = ContextPresenter.to_compact_grouped(ctx)
    assert "No related memories" in out


def test_json_includes_structural_fields() -> None:
    ctx = _ctx([_item("a", doc_type="adr")])
    import json
    payload = json.loads(ContextPresenter.to_json(ctx))
    assert payload["items"][0]["doc_type"] == "adr"
    assert "vault_scope" in payload["items"][0]
