"""Tests for cortex.documentation.routing."""

from __future__ import annotations

from pathlib import Path

import pytest

from cortex.documentation.doc_type import DocType
from cortex.documentation.errors import RoutingError, UnknownDocTypeError
from cortex.documentation.routing import (
    DOC_TYPE_ROUTING,
    list_all_routes,
    render_filename,
    resolve_route,
    resolve_target_path,
    routes_by_subfolder,
)


# --- Table integrity -------------------------------------------------------


def test_all_doc_types_in_routing_table() -> None:
    missing = [dt for dt in DocType if dt not in DOC_TYPE_ROUTING]
    assert missing == [], f"Missing routes: {missing}"


def test_routing_table_has_exactly_12_entries() -> None:
    assert len(DOC_TYPE_ROUTING) == 12


def test_each_route_has_consistent_doc_type() -> None:
    """Map key matches the spec.doc_type field."""
    for dt, spec in DOC_TYPE_ROUTING.items():
        assert spec.doc_type == dt


# --- resolve_route ---------------------------------------------------------


def test_resolve_route_returns_correct_spec() -> None:
    spec = resolve_route(DocType.ADR)
    assert spec.doc_type == DocType.ADR
    assert spec.subfolder == "decisions"


def test_resolve_route_unknown_raises() -> None:
    # Build a fake enum-like value not in DOC_TYPE_ROUTING.
    class FakeDocType:
        value = "fake"

        def __repr__(self) -> str:
            return "FakeDocType.FAKE"

    with pytest.raises(UnknownDocTypeError):
        resolve_route(FakeDocType())  # type: ignore[arg-type]


# --- render_filename -------------------------------------------------------


def test_render_filename_adr() -> None:
    spec = resolve_route(DocType.ADR)
    assert render_filename(spec, {"number": 7, "slug": "foo"}) == "ADR-007-foo.md"


def test_render_filename_decision() -> None:
    spec = resolve_route(DocType.DECISION)
    assert (
        render_filename(spec, {"date": "2026-05-14", "slug": "foo"})
        == "DEC-2026-05-14-foo.md"
    )


def test_render_filename_session() -> None:
    spec = resolve_route(DocType.SESSION)
    assert (
        render_filename(
            spec,
            {"date": "2026-05-14", "session_id": "abc123", "slug": "foo"},
        )
        == "2026-05-14_abc123_foo.md"
    )


def test_render_filename_incident_with_zero_padding() -> None:
    spec = resolve_route(DocType.INCIDENT)
    assert (
        render_filename(
            spec, {"number": 12, "date": "2026-05-14", "slug": "auth"}
        )
        == "INC-012-2026-05-14-auth.md"
    )


def test_render_filename_glossary() -> None:
    spec = resolve_route(DocType.GLOSSARY)
    assert (
        render_filename(spec, {"term_slug": "ubiquitous-language"})
        == "ubiquitous-language.md"
    )


def test_render_filename_changelog() -> None:
    spec = resolve_route(DocType.CHANGELOG)
    assert render_filename(spec, {"version": "v1.2.3"}) == "v1.2.3.md"


def test_render_filename_hu() -> None:
    spec = resolve_route(DocType.HU)
    assert render_filename(spec, {"external_id": "PROJ-1234"}) == "HU-PROJ-1234.md"


def test_render_filename_missing_placeholder_raises() -> None:
    spec = resolve_route(DocType.ADR)
    with pytest.raises(RoutingError, match="number"):
        render_filename(spec, {"slug": "foo"})


def test_render_filename_extra_placeholders_ignored() -> None:
    """Extra context keys not in the template are silently ignored."""
    spec = resolve_route(DocType.ADR)
    result = render_filename(
        spec, {"number": 7, "slug": "foo", "irrelevant": "value"}
    )
    assert result == "ADR-007-foo.md"


def test_render_filename_bad_format_value_raises() -> None:
    """A non-int value for ``number`` triggers RoutingError."""
    spec = resolve_route(DocType.ADR)
    with pytest.raises(RoutingError):
        render_filename(spec, {"number": "seven", "slug": "foo"})


# --- resolve_target_path ---------------------------------------------------


def test_resolve_target_path_local() -> None:
    spec = resolve_route(DocType.ADR)
    path = resolve_target_path(
        spec, {"number": 7, "slug": "foo"}, Path("/tmp/vault")
    )
    assert path == Path("/tmp/vault/decisions/ADR-007-foo.md")


def test_resolve_target_path_enterprise_with_project_id() -> None:
    spec = resolve_route(DocType.ADR)
    path = resolve_target_path(
        spec,
        {"number": 7, "slug": "foo"},
        Path("/tmp/vault"),
        vault_scope="enterprise",
        project_id="mi-proyecto",
    )
    assert path == Path("/tmp/vault/decisions/mi-proyecto/ADR-007-foo.md")


def test_resolve_target_path_enterprise_without_project_id_raises() -> None:
    spec = resolve_route(DocType.ADR)
    with pytest.raises(RoutingError, match="project_id"):
        resolve_target_path(
            spec, {"number": 7, "slug": "foo"},
            Path("/tmp/vault"), vault_scope="enterprise", project_id=None,
        )


def test_resolve_target_path_non_promotable_enterprise_raises() -> None:
    """HU has no enterprise_subfolder; enterprise scope raises."""
    spec = resolve_route(DocType.HU)
    with pytest.raises(RoutingError, match="not promotable"):
        resolve_target_path(
            spec, {"external_id": "PROJ-1"},
            Path("/tmp/vault"), vault_scope="enterprise", project_id="p",
        )


def test_resolve_target_path_handoff_enterprise_raises() -> None:
    spec = resolve_route(DocType.HANDOFF)
    with pytest.raises(RoutingError, match="not promotable"):
        resolve_target_path(
            spec, {"date": "2026-05-14", "slug": "foo"},
            Path("/tmp/vault"), vault_scope="enterprise", project_id="p",
        )


def test_resolve_target_path_glossary_enterprise_no_project_namespacing() -> None:
    """Glossary has enterprise_subfolder='glossary' (no {project_id})."""
    spec = resolve_route(DocType.GLOSSARY)
    path = resolve_target_path(
        spec,
        {"term_slug": "doctype"},
        Path("/tmp/vault"),
        vault_scope="enterprise",
        project_id="any",
    )
    assert path == Path("/tmp/vault/glossary/doctype.md")


def test_resolve_target_path_invalid_scope_raises() -> None:
    spec = resolve_route(DocType.ADR)
    with pytest.raises(RoutingError, match="vault_scope"):
        resolve_target_path(
            spec, {"number": 7, "slug": "foo"},
            Path("/tmp/vault"), vault_scope="shared",
        )


# --- list_all_routes / routes_by_subfolder ---------------------------------


def test_list_all_routes_returns_12() -> None:
    routes = list_all_routes()
    assert len(routes) == 12


def test_routes_by_subfolder_groups_decisions() -> None:
    grouped = routes_by_subfolder()
    assert "decisions" in grouped
    assert len(grouped["decisions"]) == 2
    types = {spec.doc_type for spec in grouped["decisions"]}
    assert types == {DocType.ADR, DocType.DECISION}


def test_subfolders_mostly_unique() -> None:
    """Only 'decisions' has two doc_types; all others are unique."""
    grouped = routes_by_subfolder()
    duplicates = [k for k, v in grouped.items() if len(v) > 1]
    assert duplicates == ["decisions"]


# --- Per-type assertions ---------------------------------------------------


def test_hu_not_promotable() -> None:
    spec = resolve_route(DocType.HU)
    assert spec.promotable is False
    assert spec.enterprise_subfolder is None


def test_handoff_not_promotable() -> None:
    spec = resolve_route(DocType.HANDOFF)
    assert spec.promotable is False


def test_adr_retrieval_boost_per_intent_populated() -> None:
    spec = resolve_route(DocType.ADR)
    assert spec.retrieval_boost_per_intent["decision"] == 2.0
    assert spec.retrieval_boost_per_intent["architecture"] == 1.5


def test_runbook_requires_review() -> None:
    spec = resolve_route(DocType.RUNBOOK)
    assert spec.requires_review_before_publish is True
    assert spec.promotion_mode == "review-required"
    assert spec.auto_expire_days == 180


def test_session_chunking_disabled() -> None:
    spec = resolve_route(DocType.SESSION)
    assert spec.chunking_enabled is False


def test_glossary_enterprise_subfolder_no_placeholder() -> None:
    spec = resolve_route(DocType.GLOSSARY)
    assert spec.enterprise_subfolder == "glossary"
    assert "{project_id}" not in spec.enterprise_subfolder


def test_all_routes_have_template_path_attribute() -> None:
    """Every RouteSpec has a non-None template_path (existence checked in Fase 03)."""
    for spec in list_all_routes():
        assert spec.template_path is not None
        assert isinstance(spec.template_path, Path)
