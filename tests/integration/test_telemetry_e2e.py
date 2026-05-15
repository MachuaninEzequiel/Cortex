"""End-to-end integration test for the Fase 05 telemetry pipeline.

Wires together:
    - ContextEnricher with PersistentObserver
    - Session note writer with cortex_telemetry frontmatter
    - PersistentObserver.aggregate for the report side

Verifies the full lifecycle: enrich -> persist event -> cite items via
session body -> record citations -> aggregate.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from cortex.context_enricher.enricher import ContextEnricher
from cortex.context_enricher.telemetry import (
    PersistentObserver,
    detect_citations,
    make_observer,
)
import uuid

from cortex.documentation import parse_frontmatter_lenient, write_session_note_canonical
from cortex.documentation.data import SessionData
from cortex.models import EnrichedContext, EnrichedItem, WorkContext


class _PathOnlyVault:
    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def path(self) -> Path:
        return self._root

    def index_file(self, relative_path: str) -> bool:
        return False


def _make_work() -> WorkContext:
    return WorkContext(
        source="manual", changed_files=[], keywords=[], search_queries=[],
    )


def test_full_pipeline_enrich_cite_aggregate(tmp_path: Path) -> None:
    """Run enrich -> cite -> aggregate end-to-end."""
    obs = PersistentObserver(tmp_path / ".cortex" / "events.jsonl")

    # Enrich produces a run_id and an event in the JSONL.
    enricher = ContextEnricher(
        episodic=MagicMock(), semantic=MagicMock(), observer=obs,
    )
    work = _make_work()
    ctx = enricher.enrich(work)
    assert ctx.enricher_run_id is not None

    # Manually craft a session body that cites two items.
    items_offered = [
        {"source_id": "decisions/ADR-007-foo.md"},
        {"source_id": "decisions/ADR-001-foo.md"},
        {"source_id": "decisions/ADR-999-foo.md"},
    ]
    body = "See [[ADR-007-foo]] and [link](decisions/ADR-001-foo.md)."
    cited = detect_citations(body, items_offered)
    assert cited == [
        "decisions/ADR-007-foo.md", "decisions/ADR-001-foo.md",
    ]
    for sid in cited:
        obs.record_citation(ctx.enricher_run_id, sid)

    # Aggregate confirms what the agent used.
    agg = obs.aggregate()
    assert agg["enrichments"] == 1
    assert agg["citations"] == 2


def test_make_observer_returns_disabled_via_config(tmp_path: Path) -> None:
    """When the config sets enabled=False, make_observer yields a no-op observer."""
    layout = SimpleNamespace(workspace_root=tmp_path)
    config = {"retrieval": {"telemetry": {"enabled": False}}}
    obs = make_observer(layout, config=config)
    ctx = EnrichedContext(work=_make_work(), items=[], total_items=0)
    rid = obs.record_enrichment(ctx)
    assert rid == ""
    assert not (tmp_path / ".cortex" / "enrichment-events.jsonl").exists()


def test_session_persists_telemetry_block_in_frontmatter(tmp_path: Path) -> None:
    """write_session_note_canonical round-trips a cortex_telemetry block."""
    telemetry = {
        "enricher_run_id": "abc123",
        "context_items_offered": 5,
        "context_items_used": 2,
        "context_hit_rate": 0.4,
        "context_by_type": {"adr": 1, "runbook": 1},
        "context_by_strategy": {"topic_search": 1},
        "context_by_scope": {"local": 2},
        "enriched_score_p50": 0.5,
        "enriched_score_p95": 0.8,
        "enricher_latency_ms": 120,
    }
    data = SessionData(
        title="Integration test",
        tags=["session"],
        status="completed",
        session_id=uuid.uuid4().hex[:12],
        spec_summary="E2E telemetry",
        cortex_telemetry=telemetry,
    )
    path = write_session_note_canonical(data, vault=_PathOnlyVault(tmp_path))
    fm = parse_frontmatter_lenient(path)
    assert fm["cortex_telemetry"]["enricher_run_id"] == "abc123"
    assert fm["cortex_telemetry"]["enricher_latency_ms"] == 120


def test_enricher_observer_records_real_items(tmp_path: Path) -> None:
    """A populated EnrichedContext propagates items_offered to the JSONL."""
    obs = PersistentObserver(tmp_path / ".cortex" / "events.jsonl")
    work = _make_work()
    items = [
        EnrichedItem(
            source="episodic", source_id=f"i-{i}", title=f"item-{i}",
            content="body", score=0.5, enriched_score=0.5,
            matched_by=["topic_search"], files_mentioned=[], tags=["tag"],
        )
        for i in range(3)
    ]
    ctx = EnrichedContext(
        work=work, items=items,
        total_searches=1, total_raw_hits=3, total_items=3,
        total_chars=300, within_budget=True,
    )
    rid = obs.record_enrichment(ctx, latency_ms=42)
    events = obs.iter_events()
    assert len(events) == 1
    assert events[0]["run_id"] == rid
    assert len(events[0]["items_offered"]) == 3
    assert events[0]["items_offered"][0]["source_id"] == "i-0"
