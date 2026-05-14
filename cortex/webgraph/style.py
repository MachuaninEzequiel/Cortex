"""cortex.webgraph.style - Node and edge styling for the canonical webgraph.

Maps ``DocType`` instances and edge classifications to colors and shapes so
the visualization layer can render the graph with semantic differentiation.

Colors come from each ``RouteSpec.webgraph_color`` and shapes from
``RouteSpec.webgraph_shape`` (defined in
``cortex.documentation.routing.DOC_TYPE_ROUTING``). This module exists so the
visualization layer doesn't need to know about the routing table directly —
it just calls ``style_for_doc_type(doc_type)`` and gets back a ``NodeStyle``.
"""

from __future__ import annotations

from dataclasses import dataclass

from cortex.documentation.doc_type import DocType

# Fallback style for legacy nodes without a DocType.
_DEFAULT_NODE_COLOR = "#cccccc"
_DEFAULT_NODE_SHAPE = "ellipse"


@dataclass(frozen=True)
class NodeStyle:
    """Visual styling for a node in the webgraph."""

    color: str
    shape: str


def style_for_doc_type(doc_type: DocType | str | None) -> NodeStyle:
    """Resolve a ``NodeStyle`` for a DocType.

    Accepts either a ``DocType`` enum, its string slug, or ``None``. Unknown
    values yield the default gray ellipse so the visualization keeps working
    for legacy or unclassifiable nodes.
    """
    if doc_type is None:
        return NodeStyle(color=_DEFAULT_NODE_COLOR, shape=_DEFAULT_NODE_SHAPE)

    if isinstance(doc_type, str):
        try:
            doc_type = DocType(doc_type)
        except ValueError:
            return NodeStyle(color=_DEFAULT_NODE_COLOR, shape=_DEFAULT_NODE_SHAPE)

    try:
        # Lazy import to avoid a circular dependency between webgraph and routing.
        from cortex.documentation.routing import resolve_route
        route = resolve_route(doc_type)
        return NodeStyle(color=route.webgraph_color, shape=route.webgraph_shape)
    except Exception:
        return NodeStyle(color=_DEFAULT_NODE_COLOR, shape=_DEFAULT_NODE_SHAPE)


# ---------------------------------------------------------------------------
# Edge types
# ---------------------------------------------------------------------------


EDGE_TYPES: dict[str, dict[str, str]] = {
    "wiki_link": {
        "color": "#666666",
        "style": "solid",
        "label": "links to",
    },
    "co_occurrence": {
        "color": "#aaaaaa",
        "style": "dashed",
        "label": "co-occurs",
    },
    "imports": {
        "color": "#88aaff",
        "style": "solid",
        "label": "imports",
    },
    "tested_by": {
        "color": "#88dd88",
        "style": "dotted",
        "label": "tested by",
    },
    "supersedes": {
        "color": "#dd6666",
        "style": "solid",
        "label": "supersedes",
    },
    "promoted_from": {
        "color": "#aa66cc",
        "style": "dashed",
        "label": "promoted from",
    },
}


def style_for_edge(edge_type: str) -> dict[str, str]:
    """Resolve a style dict for an edge classification.

    Unknown edge types yield a neutral gray solid style so the visualization
    keeps working when new edge classifications appear before this table is
    updated.
    """
    return EDGE_TYPES.get(edge_type, {
        "color": _DEFAULT_NODE_COLOR,
        "style": "solid",
        "label": edge_type,
    })


# ---------------------------------------------------------------------------
# Legend
# ---------------------------------------------------------------------------


def build_legend() -> dict[str, list[dict[str, str]]]:
    """Build a legend payload suitable for embedding in a webgraph snapshot.

    Returns a dict with two keys:

    - ``doc_types``: one entry per DocType with its color, shape and slug.
    - ``edge_types``: one entry per known edge classification.
    """
    doc_types_entries: list[dict[str, str]] = []
    for dt in DocType:
        style = style_for_doc_type(dt)
        doc_types_entries.append({
            "type": dt.value,
            "color": style.color,
            "shape": style.shape,
        })

    edge_entries: list[dict[str, str]] = [
        {"type": k, **v} for k, v in EDGE_TYPES.items()
    ]

    return {"doc_types": doc_types_entries, "edge_types": edge_entries}


__all__ = [
    "EDGE_TYPES",
    "NodeStyle",
    "build_legend",
    "style_for_doc_type",
    "style_for_edge",
]
