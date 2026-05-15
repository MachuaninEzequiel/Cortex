"""Tests for the shared CLI/MCP search filter helper (Item #7 deuda residual)."""

from __future__ import annotations

import pytest

from cortex.cli._search_filters import (
    build_enrichment_filters_from_cli,
    has_any_filter,
)
from cortex.documentation.doc_type import DocType


def test_build_filters_translates_doc_type_slugs() -> None:
    filters = build_enrichment_filters_from_cli(
        doc_type=["adr", "runbook"],
        exclude_doc_type=["session"],
        status=["accepted"],
        tag=["release"],
        tag_any=["important"],
        scope="enterprise",
        max_age_days=30,
        project_id=["acme"],
        strict=True,
    )
    assert filters.doc_types == [DocType.ADR, DocType.RUNBOOK]
    assert filters.exclude_doc_types == [DocType.SESSION]
    assert filters.statuses_allowed == ["accepted"]
    assert filters.tags_required == ["release"]
    assert filters.tags_any_of == ["important"]
    assert filters.vault_scope == "enterprise"
    assert filters.max_age_days == 30
    assert filters.project_ids == ["acme"]
    assert filters.strict is True


def test_build_filters_empty_lists_become_none() -> None:
    filters = build_enrichment_filters_from_cli(
        doc_type=[],
        exclude_doc_type=[],
        status=[],
        tag=[],
        tag_any=[],
        scope="local",
        max_age_days=None,
        project_id=[],
        strict=False,
    )
    assert filters.doc_types is None
    assert filters.statuses_allowed is None
    assert filters.project_ids is None


def test_build_filters_rejects_unknown_doc_type() -> None:
    with pytest.raises(ValueError, match="--doc-type"):
        build_enrichment_filters_from_cli(
            doc_type=["banana"],
            exclude_doc_type=None,
            status=None,
            tag=None,
            tag_any=None,
            scope="local",
            max_age_days=None,
            project_id=None,
            strict=False,
        )


def test_build_filters_rejects_invalid_scope() -> None:
    with pytest.raises(ValueError, match="--scope"):
        build_enrichment_filters_from_cli(
            doc_type=None,
            exclude_doc_type=None,
            status=None,
            tag=None,
            tag_any=None,
            scope="planet",
            max_age_days=None,
            project_id=None,
            strict=False,
        )


def test_has_any_filter_returns_false_for_legacy_invocation() -> None:
    assert not has_any_filter(
        doc_type=None,
        exclude_doc_type=None,
        status=None,
        tag=None,
        tag_any=None,
        max_age_days=None,
        project_id=None,
        strict=False,
        scope="local",
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"doc_type": ["adr"]},
        {"exclude_doc_type": ["session"]},
        {"status": ["accepted"]},
        {"tag": ["release"]},
        {"tag_any": ["important"]},
        {"max_age_days": 5},
        {"strict": True},
    ],
)
def test_has_any_filter_detects_each_structural_flag(kwargs: dict[str, object]) -> None:
    base = dict(
        doc_type=None,
        exclude_doc_type=None,
        status=None,
        tag=None,
        tag_any=None,
        max_age_days=None,
        project_id=None,
        strict=False,
        scope="local",
    )
    base.update(kwargs)
    assert has_any_filter(**base)  # type: ignore[arg-type]
