"""Tests for ContextEnricher filters + DocIntent boost (Fase 08)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cortex.context_enricher.enricher import ContextEnricher
from cortex.context_enricher.filters import EnrichmentFilters
from cortex.documentation.doc_type import DocType
from cortex.models import EnrichedItem, WorkContext


def _items(*specs: dict) -> list[EnrichedItem]:
    out = []
    for s in specs:
        out.append(EnrichedItem(
            source=s.get("source", "semantic"),
            source_id=s["id"],
            title=s.get("title", s["id"]),
            content=s.get("content", "body"),
            score=s.get("score", 0.5),
            enriched_score=s.get("enriched_score", 0.5),
            matched_by=s.get("matched_by", ["topic_search"]),
            tags=s.get("tags", []),
            doc_type=s.get("doc_type"),
            status=s.get("status"),
            vault_scope=s.get("vault_scope", "local"),
        ))
    return out


def _make_enricher() -> ContextEnricher:
    return ContextEnricher(
        episodic=MagicMock(),
        semantic=MagicMock(),
    )


def _patch_search(enricher: ContextEnricher, items: list[EnrichedItem]) -> None:
    """Bypass the multi-strategy pipeline by injecting items directly."""
    def fake_search(query, top_k):
        return [_item_to_unified(it) for it in items]
    enricher._search_hybrid = fake_search  # type: ignore[method-assign]


def _item_to_unified(item: EnrichedItem):
    """Wrap an EnrichedItem as a minimal UnifiedHit so the enricher can ingest it."""
    from cortex.models import UnifiedHit, SemanticDocument
    return UnifiedHit(
        source=item.source,  # type: ignore[arg-type]
        score=item.score,
        doc=SemanticDocument(
            path=item.source_id,
            title=item.title,
            content=item.content,
            tags=item.tags,
            score=item.score,  # <-- enricher reads hit.doc.score for semantic items
        ) if item.source == "semantic" else None,
        entry=None,
    )


# ---------------------------------------------------------------------------
# Filters applied through enrich()
# ---------------------------------------------------------------------------


def test_enrich_with_filters_drops_excluded_types() -> None:
    enricher = _make_enricher()
    items = _items(
        {"id": "decisions/adr-1.md", "doc_type": "adr", "tags": ["security"]},
        {"id": "runbooks/rb-1.md", "doc_type": "runbook", "tags": ["security"]},
    )
    _patch_search(enricher, items)
    work = WorkContext(
        source="manual",
        changed_files=[],
        keywords=["security"],
        search_queries=["security review"],
    )
    ctx = enricher.enrich(
        work,
        filters=EnrichmentFilters(doc_types=[DocType.ADR]),
    )
    ids = [i.source_id for i in ctx.items]
    assert "decisions/adr-1.md" in ids
    assert "runbooks/rb-1.md" not in ids


def test_enrich_without_filters_keeps_everything() -> None:
    enricher = _make_enricher()
    items = _items(
        {"id": "decisions/adr-1.md", "doc_type": "adr"},
        {"id": "runbooks/rb-1.md", "doc_type": "runbook"},
    )
    _patch_search(enricher, items)
    work = WorkContext(
        source="manual", changed_files=[], keywords=["x"], search_queries=["x"],
    )
    ctx = enricher.enrich(work)
    assert len(ctx.items) == 2


# ---------------------------------------------------------------------------
# DocIntent boost
# ---------------------------------------------------------------------------


def test_doc_intent_decision_boosts_adr() -> None:
    enricher = _make_enricher()
    items = _items(
        {"id": "decisions/adr-1.md", "doc_type": "adr", "score": 0.5, "enriched_score": 0.5},
        {"id": "sessions/s-1.md", "doc_type": "session", "score": 0.5, "enriched_score": 0.5},
    )
    _patch_search(enricher, items)
    work = WorkContext(
        source="manual", changed_files=[], keywords=[],
        search_queries=["why did we choose this approach?"],
    )
    ctx = enricher.enrich(work)
    adr = next(i for i in ctx.items if i.doc_type == "adr")
    # DECISION intent boosts ADR by 2.0x in the canonical routing table.
    assert adr.enriched_score > 0.5
    assert adr.enriched_score == pytest.approx(0.5 * 2.0, rel=0.1)


def test_doc_intent_runbook_boosts_runbook() -> None:
    enricher = _make_enricher()
    items = _items(
        {"id": "runbooks/rb-1.md", "doc_type": "runbook",
         "score": 0.4, "enriched_score": 0.4},
    )
    _patch_search(enricher, items)
    work = WorkContext(
        source="manual", changed_files=[], keywords=[],
        search_queries=["how do I deploy the service?"],
    )
    ctx = enricher.enrich(work)
    rb = ctx.items[0]
    # RUNBOOK intent boosts runbooks by 2.5x.
    assert rb.enriched_score > 0.4
    assert rb.enriched_score == pytest.approx(0.4 * 2.5, rel=0.1)


def test_no_intent_no_boost() -> None:
    enricher = _make_enricher()
    items = _items(
        {"id": "decisions/adr-1.md", "doc_type": "adr",
         "score": 0.5, "enriched_score": 0.5},
    )
    _patch_search(enricher, items)
    work = WorkContext(
        source="manual", changed_files=[], keywords=[],
        search_queries=["hello world"],
    )
    ctx = enricher.enrich(work)
    # GENERIC intent leaves the score untouched.
    assert ctx.items[0].enriched_score == pytest.approx(0.5)


def test_item_without_doc_type_not_boosted() -> None:
    enricher = _make_enricher()
    items = _items(
        {"id": "legacy/x.md", "doc_type": None,
         "score": 0.5, "enriched_score": 0.5},
    )
    _patch_search(enricher, items)
    work = WorkContext(
        source="manual", changed_files=[], keywords=[],
        search_queries=["why did we choose this?"],
    )
    ctx = enricher.enrich(work)
    assert ctx.items[0].enriched_score == pytest.approx(0.5)
