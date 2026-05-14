"""Tests for cortex.context_enricher.filters (Fase 08)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from cortex.context_enricher.filters import EnrichmentFilters, apply_filters
from cortex.documentation.doc_type import DocType
from cortex.models import EnrichedItem


def _item(
    source_id: str,
    *,
    doc_type: str | None = None,
    status: str | None = None,
    vault_scope: str = "local",
    tags: list[str] | None = None,
    date: datetime | None = None,
    origin_project_id: str | None = None,
    source: str = "semantic",
) -> EnrichedItem:
    return EnrichedItem(
        source=source,
        source_id=source_id,
        title=f"Item {source_id}",
        content=f"body of {source_id}",
        score=0.5,
        enriched_score=0.5,
        matched_by=["topic_search"],
        files_mentioned=[],
        date=date,
        tags=list(tags or []),
        doc_type=doc_type,
        status=status,
        vault_scope=vault_scope,
        origin_project_id=origin_project_id,
    )


# ---------------------------------------------------------------------------
# Default / empty filters
# ---------------------------------------------------------------------------


def test_no_filters_returns_input_as_list() -> None:
    items = [_item("1"), _item("2")]
    assert apply_filters(items, None) == items
    assert apply_filters(items, EnrichmentFilters()) == items


def test_is_empty_detects_default_filters() -> None:
    assert EnrichmentFilters().is_empty()
    assert not EnrichmentFilters(doc_types=[DocType.ADR]).is_empty()


# ---------------------------------------------------------------------------
# doc_types / exclude_doc_types
# ---------------------------------------------------------------------------


def test_doc_types_keeps_only_matching() -> None:
    items = [_item("a", doc_type="adr"), _item("b", doc_type="runbook")]
    out = apply_filters(items, EnrichmentFilters(doc_types=[DocType.ADR]))
    assert [i.source_id for i in out] == ["a"]


def test_doc_types_keeps_items_with_none_when_not_strict() -> None:
    items = [_item("a", doc_type="adr"), _item("legacy", doc_type=None)]
    out = apply_filters(items, EnrichmentFilters(doc_types=[DocType.ADR]))
    assert {i.source_id for i in out} == {"a", "legacy"}


def test_strict_excludes_none_doc_type() -> None:
    items = [_item("a", doc_type="adr"), _item("legacy", doc_type=None)]
    out = apply_filters(
        items, EnrichmentFilters(doc_types=[DocType.ADR], strict=True),
    )
    assert [i.source_id for i in out] == ["a"]


def test_exclude_doc_types() -> None:
    items = [_item("a", doc_type="adr"), _item("b", doc_type="runbook")]
    out = apply_filters(items, EnrichmentFilters(exclude_doc_types=[DocType.ADR]))
    assert [i.source_id for i in out] == ["b"]


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


def test_statuses_allowed_keeps_match() -> None:
    items = [_item("a", status="accepted"), _item("b", status="proposed")]
    out = apply_filters(items, EnrichmentFilters(statuses_allowed=["accepted"]))
    assert [i.source_id for i in out] == ["a"]


def test_statuses_excluded_drops_match() -> None:
    items = [_item("a", status="accepted"), _item("b", status="rejected")]
    out = apply_filters(items, EnrichmentFilters(statuses_excluded=["rejected"]))
    assert [i.source_id for i in out] == ["a"]


def test_statuses_allowed_excludes_items_without_status() -> None:
    items = [_item("a", status=None), _item("b", status="accepted")]
    out = apply_filters(items, EnrichmentFilters(statuses_allowed=["accepted"]))
    assert [i.source_id for i in out] == ["b"]


# ---------------------------------------------------------------------------
# tags
# ---------------------------------------------------------------------------


def test_tags_required_AND() -> None:
    items = [
        _item("a", tags=["security", "auth"]),
        _item("b", tags=["security"]),
        _item("c", tags=["auth"]),
    ]
    out = apply_filters(
        items, EnrichmentFilters(tags_required=["security", "auth"]),
    )
    assert [i.source_id for i in out] == ["a"]


def test_tags_any_of_OR() -> None:
    items = [
        _item("a", tags=["security"]),
        _item("b", tags=["auth"]),
        _item("c", tags=["other"]),
    ]
    out = apply_filters(
        items, EnrichmentFilters(tags_any_of=["security", "auth"]),
    )
    assert {i.source_id for i in out} == {"a", "b"}


def test_tags_excluded_drops_match() -> None:
    items = [_item("a", tags=["draft"]), _item("b", tags=["ok"])]
    out = apply_filters(items, EnrichmentFilters(tags_excluded=["draft"]))
    assert [i.source_id for i in out] == ["b"]


# ---------------------------------------------------------------------------
# scope
# ---------------------------------------------------------------------------


def test_scope_local_filters_out_enterprise() -> None:
    items = [_item("a", vault_scope="local"), _item("b", vault_scope="enterprise")]
    out = apply_filters(items, EnrichmentFilters(vault_scope="local"))
    assert [i.source_id for i in out] == ["a"]


def test_scope_all_keeps_both() -> None:
    items = [_item("a", vault_scope="local"), _item("b", vault_scope="enterprise")]
    out = apply_filters(items, EnrichmentFilters(vault_scope="all"))
    assert len(out) == 2


# ---------------------------------------------------------------------------
# max_age_days
# ---------------------------------------------------------------------------


def test_max_age_drops_old_items() -> None:
    now = datetime.now(UTC)
    items = [
        _item("recent", date=now - timedelta(days=5)),
        _item("old", date=now - timedelta(days=120)),
    ]
    out = apply_filters(items, EnrichmentFilters(max_age_days=30))
    assert [i.source_id for i in out] == ["recent"]


def test_max_age_keeps_items_without_date() -> None:
    items = [_item("no_date"), _item("old", date=datetime.now(UTC) - timedelta(days=120))]
    out = apply_filters(items, EnrichmentFilters(max_age_days=30))
    assert "no_date" in [i.source_id for i in out]


def test_max_age_naive_datetime_treated_as_utc() -> None:
    now = datetime.now()  # naive
    items = [_item("naive_old", date=now - timedelta(days=120))]
    out = apply_filters(items, EnrichmentFilters(max_age_days=30))
    assert out == []


def test_max_age_zero_or_none_is_noop() -> None:
    """``max_age_days=0`` (i.e. no filter) leaves items untouched."""
    items = [_item("old", date=datetime.now(UTC) - timedelta(days=120))]
    out = apply_filters(items, EnrichmentFilters(max_age_days=0))
    assert out == items


# ---------------------------------------------------------------------------
# project_ids
# ---------------------------------------------------------------------------


def test_project_ids_filter() -> None:
    items = [
        _item("a", origin_project_id="proj-a"),
        _item("b", origin_project_id="proj-b"),
        _item("c", origin_project_id=None),
    ]
    out = apply_filters(items, EnrichmentFilters(project_ids=["proj-a"]))
    assert [i.source_id for i in out] == ["a"]


# ---------------------------------------------------------------------------
# AND composition
# ---------------------------------------------------------------------------


def test_combined_filters_AND() -> None:
    items = [
        _item("a", doc_type="adr", status="accepted", tags=["security"]),
        _item("b", doc_type="adr", status="rejected", tags=["security"]),
        _item("c", doc_type="runbook", status="accepted", tags=["security"]),
    ]
    filters = EnrichmentFilters(
        doc_types=[DocType.ADR],
        statuses_allowed=["accepted"],
        tags_required=["security"],
    )
    out = apply_filters(items, filters)
    assert [i.source_id for i in out] == ["a"]


def test_apply_filters_does_not_mutate_input() -> None:
    items = [_item("a", doc_type="adr"), _item("b", doc_type="runbook")]
    apply_filters(items, EnrichmentFilters(doc_types=[DocType.ADR]))
    # Original list unchanged.
    assert [i.source_id for i in items] == ["a", "b"]
