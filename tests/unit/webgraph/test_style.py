"""Tests for cortex.webgraph.style (Fase 09)."""

from __future__ import annotations

import pytest

from cortex.documentation.doc_type import DocType
from cortex.documentation.routing import resolve_route
from cortex.webgraph.style import (
    EDGE_TYPES,
    NodeStyle,
    build_legend,
    style_for_doc_type,
    style_for_edge,
)


# ---------------------------------------------------------------------------
# style_for_doc_type
# ---------------------------------------------------------------------------


def test_style_resolves_known_doctype_to_route_color() -> None:
    style = style_for_doc_type(DocType.ADR)
    expected = resolve_route(DocType.ADR)
    assert style.color == expected.webgraph_color
    assert style.shape == expected.webgraph_shape


def test_style_accepts_string_slug() -> None:
    assert style_for_doc_type("adr") == style_for_doc_type(DocType.ADR)


def test_style_unknown_slug_returns_default() -> None:
    style = style_for_doc_type("bogus")
    assert style.color == "#cccccc"
    assert style.shape == "ellipse"


def test_style_none_returns_default() -> None:
    style = style_for_doc_type(None)
    assert style == NodeStyle(color="#cccccc", shape="ellipse")


def test_style_every_doc_type_resolves() -> None:
    for dt in DocType:
        s = style_for_doc_type(dt)
        # All canonical DocTypes have a non-default color.
        assert s.color != "#cccccc"


# ---------------------------------------------------------------------------
# style_for_edge
# ---------------------------------------------------------------------------


def test_style_for_edge_known() -> None:
    s = style_for_edge("wiki_link")
    assert s["color"] == EDGE_TYPES["wiki_link"]["color"]
    assert s["style"] == "solid"


def test_style_for_edge_unknown_returns_fallback() -> None:
    s = style_for_edge("unknown_relation")
    assert s["color"] == "#cccccc"
    assert s["style"] == "solid"
    assert s["label"] == "unknown_relation"


def test_edge_types_cover_canonical_set() -> None:
    expected = {"wiki_link", "co_occurrence", "imports", "tested_by", "supersedes", "promoted_from"}
    assert expected.issubset(EDGE_TYPES.keys())


# ---------------------------------------------------------------------------
# build_legend
# ---------------------------------------------------------------------------


def test_legend_contains_all_doc_types() -> None:
    legend = build_legend()
    types_in_legend = {entry["type"] for entry in legend["doc_types"]}
    # Legend includes the 12 canonical DocTypes plus synthetic entries
    # (currently ``episodic`` — Item #6 deuda residual).
    assert {dt.value for dt in DocType}.issubset(types_in_legend)
    assert "episodic" in types_in_legend


def test_legend_contains_edge_types() -> None:
    legend = build_legend()
    edges_in_legend = {entry["type"] for entry in legend["edge_types"]}
    assert "wiki_link" in edges_in_legend
    assert "supersedes" in edges_in_legend


def test_legend_each_doctype_has_color_and_shape() -> None:
    legend = build_legend()
    for entry in legend["doc_types"]:
        assert "color" in entry
        assert "shape" in entry
        assert entry["color"].startswith("#")
