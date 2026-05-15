"""Tests for cortex.context_enricher.telemetry (Fase 05)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cortex.context_enricher.telemetry import (
    PersistentObserver,
    detect_citations,
)
from cortex.models import EnrichedContext, EnrichedItem, WorkContext


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_context(items: int = 0) -> EnrichedContext:
    work = WorkContext(source="manual", changed_files=[], keywords=[], search_queries=[])
    enriched_items = [
        EnrichedItem(
            source="episodic",
            source_id=f"item-{i}",
            title=f"Item {i}",
            content=f"body {i}",
            score=0.5,
            enriched_score=0.6,
            matched_by=["topic_search"],
            files_mentioned=[],
            tags=["test"],
        )
        for i in range(items)
    ]
    return EnrichedContext(
        work=work,
        items=enriched_items,
        total_searches=1,
        total_raw_hits=items,
        total_items=items,
        total_chars=items * 100,
        within_budget=True,
    )


# ---------------------------------------------------------------------------
# PersistentObserver
# ---------------------------------------------------------------------------


def test_observer_disabled_records_nothing(tmp_path: Path) -> None:
    obs = PersistentObserver(tmp_path / "events.jsonl", enabled=False)
    ctx = _make_context(items=2)
    assert obs.record_enrichment(ctx) == ""
    assert not (tmp_path / "events.jsonl").exists()


def test_observer_record_enrichment_appends_jsonl(tmp_path: Path) -> None:
    obs = PersistentObserver(tmp_path / "events.jsonl")
    ctx = _make_context(items=2)
    run_id = obs.record_enrichment(ctx, latency_ms=42)
    assert len(run_id) == 12
    events = obs.iter_events()
    assert len(events) == 1
    ev = events[0]
    assert ev["event_type"] == "enrichment"
    assert ev["run_id"] == run_id
    assert ev["latency_ms"] == 42
    assert len(ev["items_offered"]) == 2


def test_observer_record_citation_appends_separate_event(tmp_path: Path) -> None:
    obs = PersistentObserver(tmp_path / "events.jsonl")
    ctx = _make_context(items=1)
    run_id = obs.record_enrichment(ctx)
    obs.record_citation(run_id, "item-0")
    events = obs.iter_events()
    assert len(events) == 2
    citation = events[1]
    assert citation["event_type"] == "citation"
    assert citation["run_id"] == run_id
    assert citation["source_id"] == "item-0"


def test_observer_record_citation_disabled_is_noop(tmp_path: Path) -> None:
    obs = PersistentObserver(tmp_path / "events.jsonl", enabled=False)
    obs.record_citation("any", "any")
    assert not (tmp_path / "events.jsonl").exists()


def test_observer_record_citation_empty_run_id_is_noop(tmp_path: Path) -> None:
    obs = PersistentObserver(tmp_path / "events.jsonl")
    obs.record_citation("", "item-0")
    assert obs.iter_events() == []


def test_observer_iter_events_skips_malformed_lines(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        json.dumps({"event_type": "enrichment", "run_id": "abc", "timestamp": "x"}) + "\n"
        + "not-a-json-line\n"
        + json.dumps({"event_type": "citation", "run_id": "abc", "timestamp": "y", "source_id": "s"}) + "\n",
        encoding="utf-8",
    )
    obs = PersistentObserver(path)
    events = obs.iter_events()
    assert len(events) == 2


def test_observer_iter_events_missing_file(tmp_path: Path) -> None:
    obs = PersistentObserver(tmp_path / "nope.jsonl")
    assert obs.iter_events() == []


def test_observer_events_for_run_groups_correctly(tmp_path: Path) -> None:
    obs = PersistentObserver(tmp_path / "events.jsonl")
    ctx = _make_context(items=1)
    rid = obs.record_enrichment(ctx)
    obs.record_citation(rid, "item-0")
    obs.record_citation("other-run", "item-X")
    grouped = obs.events_for_run(rid)
    assert grouped["enrichment"]["run_id"] == rid
    assert len(grouped["citations"]) == 1
    assert grouped["citations"][0]["source_id"] == "item-0"


def test_observer_aggregate_empty_returns_zeros(tmp_path: Path) -> None:
    obs = PersistentObserver(tmp_path / "events.jsonl")
    agg = obs.aggregate()
    assert agg["enrichments"] == 0
    assert agg["citations"] == 0
    assert agg["items_offered"] == 0
    assert agg["items_used"] == 0
    assert agg["hit_rate"] == 0.0
    assert agg["by_strategy"] == {}
    assert agg["latency"] == {}


def test_observer_aggregate_computes_hit_rate(tmp_path: Path) -> None:
    obs = PersistentObserver(tmp_path / "events.jsonl")
    ctx = _make_context(items=4)
    rid = obs.record_enrichment(ctx, latency_ms=100)
    obs.record_citation(rid, "item-0")
    obs.record_citation(rid, "item-2")
    agg = obs.aggregate()
    assert agg["enrichments"] == 1
    assert agg["citations"] == 2
    assert agg["items_offered"] == 4
    assert agg["items_used"] == 2
    assert agg["hit_rate"] == 0.5


def test_observer_aggregate_breaks_down_by_strategy(tmp_path: Path) -> None:
    obs = PersistentObserver(tmp_path / "events.jsonl")
    # Two items: one matched by topic, one by file_search; cite the file one.
    work = WorkContext(source="manual", changed_files=[], keywords=[], search_queries=[])
    items = [
        EnrichedItem(
            source="episodic", source_id="topic-1", title="t", content="c",
            score=0.5, enriched_score=0.5, matched_by=["topic_search"],
            files_mentioned=[], tags=[],
        ),
        EnrichedItem(
            source="semantic", source_id="file-1", title="f", content="c",
            score=0.5, enriched_score=0.5, matched_by=["file_search"],
            files_mentioned=[], tags=[],
        ),
    ]
    ctx = EnrichedContext(
        work=work, items=items, total_searches=2, total_raw_hits=2,
        total_items=2, total_chars=200, within_budget=True,
    )
    rid = obs.record_enrichment(ctx)
    obs.record_citation(rid, "file-1")
    agg = obs.aggregate()
    assert agg["by_strategy"]["topic_search"]["used"] == 0
    assert agg["by_strategy"]["topic_search"]["offered"] == 1
    assert agg["by_strategy"]["file_search"]["used"] == 1
    assert agg["by_strategy"]["file_search"]["hit_rate"] == 1.0


def test_observer_aggregate_filters_by_window(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.parent.mkdir(exist_ok=True)
    old_ts = (datetime.now(UTC) - timedelta(days=60)).isoformat()
    new_ts = datetime.now(UTC).isoformat()
    path.write_text(
        json.dumps({
            "event_type": "enrichment", "run_id": "old", "timestamp": old_ts,
            "latency_ms": 50, "total_searches": 1, "total_raw_hits": 1,
            "total_items": 1, "total_chars": 1, "within_budget": True,
            "items_offered": [{"source_id": "old", "matched_by": ["topic_search"]}],
        }) + "\n" +
        json.dumps({
            "event_type": "enrichment", "run_id": "new", "timestamp": new_ts,
            "latency_ms": 50, "total_searches": 1, "total_raw_hits": 1,
            "total_items": 1, "total_chars": 1, "within_budget": True,
            "items_offered": [{"source_id": "new", "matched_by": ["topic_search"]}],
        }) + "\n",
        encoding="utf-8",
    )
    obs = PersistentObserver(path)
    agg_all = obs.aggregate()
    assert agg_all["enrichments"] == 2
    agg_recent = obs.aggregate(since_days=30)
    assert agg_recent["enrichments"] == 1


def test_observer_latency_summary(tmp_path: Path) -> None:
    obs = PersistentObserver(tmp_path / "events.jsonl")
    for ms in [10, 20, 30, 40, 50, 100, 200]:
        ctx = _make_context(items=1)
        obs.record_enrichment(ctx, latency_ms=ms)
    agg = obs.aggregate()
    assert "p50_ms" in agg["latency"]
    assert "p95_ms" in agg["latency"]
    assert "p99_ms" in agg["latency"]
    # p50 should be 40 (median of 7 sorted values).
    assert agg["latency"]["p50_ms"] == 40


# ---------------------------------------------------------------------------
# detect_citations
# ---------------------------------------------------------------------------


def test_detect_citations_wiki_link_full_path() -> None:
    body = "See [[decisions/ADR-001-foo]] for details."
    items = [{"source_id": "decisions/ADR-001-foo.md"}]
    assert detect_citations(body, items) == ["decisions/ADR-001-foo.md"]


def test_detect_citations_wiki_link_stem_only() -> None:
    body = "See [[ADR-007-onnx]] for details."
    items = [{"source_id": "decisions/ADR-007-onnx.md"}]
    assert detect_citations(body, items) == ["decisions/ADR-007-onnx.md"]


def test_detect_citations_markdown_link() -> None:
    body = "See [the doc](decisions/ADR-001-foo.md)."
    items = [{"source_id": "decisions/ADR-001-foo.md"}]
    assert detect_citations(body, items) == ["decisions/ADR-001-foo.md"]


def test_detect_citations_handles_alias_and_anchor() -> None:
    body = "Like [[ADR-007|named ADR]] or [[ADR-007#decision]]."
    items = [{"source_id": "decisions/ADR-007.md"}]
    assert detect_citations(body, items) == ["decisions/ADR-007.md"]


def test_detect_citations_empty_body_returns_empty() -> None:
    assert detect_citations("", [{"source_id": "x.md"}]) == []


def test_detect_citations_no_offered_returns_empty() -> None:
    assert detect_citations("body with [[link]]", []) == []


def test_detect_citations_no_match() -> None:
    body = "No links here."
    items = [{"source_id": "decisions/ADR-001.md"}]
    assert detect_citations(body, items) == []


def test_detect_citations_deduplicates() -> None:
    body = "[[ADR-001]] and again [[decisions/ADR-001]] same item."
    items = [{"source_id": "decisions/ADR-001.md"}]
    assert detect_citations(body, items) == ["decisions/ADR-001.md"]


# ---------------------------------------------------------------------------
# ContextEnricher integration with observer
# ---------------------------------------------------------------------------


def test_enricher_records_event_when_observer_set(tmp_path: Path) -> None:
    from cortex.context_enricher.enricher import ContextEnricher

    obs = PersistentObserver(tmp_path / "events.jsonl")
    enricher = ContextEnricher(
        episodic=MagicMock(),
        semantic=MagicMock(),
        observer=obs,
    )
    work = WorkContext(source="manual", changed_files=[], keywords=[], search_queries=[])
    ctx = enricher.enrich(work)
    assert ctx.enricher_run_id is not None
    assert len(ctx.enricher_run_id) == 12
    assert len(obs.iter_events()) == 1


def test_enricher_no_record_when_observer_none() -> None:
    from cortex.context_enricher.enricher import ContextEnricher

    enricher = ContextEnricher(episodic=MagicMock(), semantic=MagicMock())
    work = WorkContext(source="manual", changed_files=[], keywords=[], search_queries=[])
    ctx = enricher.enrich(work)
    assert ctx.enricher_run_id is None


def test_enricher_includes_latency_in_event(tmp_path: Path) -> None:
    from cortex.context_enricher.enricher import ContextEnricher

    obs = PersistentObserver(tmp_path / "events.jsonl")
    enricher = ContextEnricher(
        episodic=MagicMock(), semantic=MagicMock(), observer=obs,
    )
    work = WorkContext(source="manual", changed_files=[], keywords=[], search_queries=[])
    enricher.enrich(work)
    ev = obs.iter_events()[0]
    assert ev["latency_ms"] is not None
    assert ev["latency_ms"] >= 0


# ---------------------------------------------------------------------------
# Session frontmatter with cortex_telemetry
# ---------------------------------------------------------------------------


def test_session_note_persists_cortex_telemetry_in_frontmatter(tmp_path: Path) -> None:
    import uuid

    from cortex.documentation import parse_frontmatter_lenient, write_session_note_canonical
    from cortex.documentation.data import SessionData

    class _PathOnlyVault:
        def __init__(self, root: Path) -> None:
            self._root = root

        @property
        def path(self) -> Path:
            return self._root

        def index_file(self, relative_path: str) -> bool:
            return False

    telemetry = {
        "enricher_run_id": "abc123def456",
        "context_items_offered": 8,
        "context_items_used": 3,
        "context_hit_rate": 0.375,
        "context_by_type": {"adr": 1, "runbook": 1, "session": 1},
        "context_by_strategy": {"topic_search": 2, "entity_search": 1},
        "context_by_scope": {"local": 3},
        "enriched_score_p50": 0.42,
        "enriched_score_p95": 0.71,
        "enricher_latency_ms": 187,
    }
    data = SessionData(
        title="Test telemetry persistence",
        tags=["session"],
        status="completed",
        session_id=uuid.uuid4().hex[:12],
        spec_summary="Verify cortex_telemetry roundtrip",
        cortex_telemetry=telemetry,
    )
    path = write_session_note_canonical(data, vault=_PathOnlyVault(tmp_path))
    fm = parse_frontmatter_lenient(path)
    assert fm["cortex_telemetry"]["enricher_run_id"] == "abc123def456"
    assert fm["cortex_telemetry"]["context_hit_rate"] == 0.375
    assert fm["cortex_telemetry"]["enricher_latency_ms"] == 187
