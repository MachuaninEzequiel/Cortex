"""Tests for typed supersedes / superseded_by webgraph edges (Item #5)."""

from __future__ import annotations

from cortex.webgraph.config import WebGraphConfig
from cortex.webgraph.contracts import SemanticRecord
from cortex.webgraph.relation_builder import RelationBuilder
from cortex.webgraph.style import EDGE_TYPES, build_legend


def _record(
    *,
    rel_path: str,
    title: str,
    adr_number: int | None = None,
    supersedes: list[str] | None = None,
    superseded_by: str | None = None,
) -> SemanticRecord:
    metadata: dict[str, object] = {}
    if adr_number is not None:
        metadata["adr_number"] = adr_number
    if supersedes is not None:
        metadata["supersedes"] = supersedes
    if superseded_by is not None:
        metadata["superseded_by"] = superseded_by
    return SemanticRecord(
        node_id=f"semantic:{rel_path}",
        node_type="semantic_doc",
        title=title,
        summary=title,
        rel_path=rel_path,
        abs_path=f"/tmp/{rel_path}",
        tags=["adr"],
        links=[],
        content=title,
        embedding=None,
        metadata=metadata,
    )


def _build_edges(records: list[SemanticRecord]):
    builder = RelationBuilder(WebGraphConfig(enable_semantic_neighbors=False))
    return builder.build_edges(records, [])


def test_supersedes_creates_typed_edge_by_adr_number() -> None:
    old = _record(rel_path="decisions/ADR-001-old.md", title="Old", adr_number=1)
    new = _record(
        rel_path="decisions/ADR-007-new.md",
        title="New",
        adr_number=7,
        supersedes=["ADR-001"],
    )
    edges = _build_edges([old, new])
    typed = [e for e in edges if e.edge_type == "supersedes"]
    assert len(typed) == 1
    assert typed[0].source == new.node_id
    assert typed[0].target == old.node_id


def test_superseded_by_emits_typed_edge() -> None:
    old = _record(
        rel_path="decisions/ADR-001-old.md",
        title="Old",
        adr_number=1,
        superseded_by="ADR-007",
    )
    new = _record(rel_path="decisions/ADR-007-new.md", title="New", adr_number=7)
    edges = _build_edges([old, new])
    typed = [e for e in edges if e.edge_type == "superseded_by"]
    assert len(typed) == 1
    assert typed[0].source == old.node_id
    assert typed[0].target == new.node_id


def test_unresolved_supersedes_target_is_skipped() -> None:
    new = _record(
        rel_path="decisions/ADR-007-new.md",
        title="New",
        adr_number=7,
        supersedes=["ADR-999"],
    )
    edges = _build_edges([new])
    assert [e for e in edges if e.edge_type == "supersedes"] == []


def test_supersedes_resolves_by_path_stem_fallback() -> None:
    old = _record(rel_path="decisions/legacy-decision.md", title="Legacy")
    new = _record(
        rel_path="decisions/ADR-007-new.md",
        title="New",
        adr_number=7,
        supersedes=["legacy-decision"],
    )
    edges = _build_edges([old, new])
    typed = [e for e in edges if e.edge_type == "supersedes"]
    assert len(typed) == 1
    assert typed[0].target == old.node_id


def test_supersedes_and_superseded_by_in_legend() -> None:
    legend = build_legend()
    edge_types = {entry["type"] for entry in legend["edge_types"]}
    assert "supersedes" in edge_types
    assert "superseded_by" in edge_types
    assert EDGE_TYPES["supersedes"]["color"] != EDGE_TYPES["superseded_by"]["color"]
