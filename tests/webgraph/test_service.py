from __future__ import annotations

from pathlib import Path

from cortex.webgraph.config import WebGraphConfig
from cortex.webgraph.episodic_source import EpisodicSource
from cortex.webgraph.semantic_source import SemanticSource
from cortex.webgraph.service import WebGraphService


def test_hybrid_snapshot_links_semantic_and_episodic(vault_reader, episodic_store, tmp_path: Path) -> None:
    episodic_store.add(
        "Specification: Auth Login Flow Goal: Refresh tokens and login middleware",
        memory_type="spec",
        tags=["spec", "auth"],
        files=["auth.md"],
    )
    episodic_store.add(
        "Session: Auth Login Flow Specification: Auth Login Flow Changes: Updated auth.md",
        memory_type="session",
        tags=["session", "auth"],
        files=["auth.md"],
    )

    config = WebGraphConfig(enable_semantic_neighbors=False)
    service = WebGraphService(
        tmp_path,
        config=config,
        semantic_source=SemanticSource(tmp_path, reader=vault_reader, embedder=vault_reader._embedder),
        episodic_source=EpisodicSource(tmp_path, store=episodic_store, embedder=episodic_store.embedder),
    )

    snapshot = service.build_snapshot(mode="hybrid", use_cache=False)

    assert any(node.source == "semantic" for node in snapshot.nodes)
    assert any(node.source == "episodic" for node in snapshot.nodes)
    assert any(edge.edge_type == "same_file_reference" for edge in snapshot.edges)


def test_subgraph_is_centered_on_requested_node(vault_reader, episodic_store, tmp_path: Path) -> None:
    episodic_store.add(
        "Specification: Auth Goal: Login flow and middleware",
        memory_type="spec",
        tags=["spec", "auth"],
        files=["auth.md"],
    )
    service = WebGraphService(
        tmp_path,
        config=WebGraphConfig(enable_semantic_neighbors=False),
        semantic_source=SemanticSource(tmp_path, reader=vault_reader, embedder=vault_reader._embedder),
        episodic_source=EpisodicSource(tmp_path, store=episodic_store, embedder=episodic_store.embedder),
    )
    snapshot = service.build_snapshot(mode="hybrid", use_cache=False)
    center = next(node.id for node in snapshot.nodes if node.source == "episodic")

    subgraph = service.get_subgraph(center, depth=1, mode="hybrid")

    assert any(node.id == center for node in subgraph.nodes)
    assert subgraph.stats.node_count <= snapshot.stats.node_count


def test_export_snapshot_writes_json(vault_reader, episodic_store, tmp_path: Path) -> None:
    service = WebGraphService(
        tmp_path,
        config=WebGraphConfig(enable_semantic_neighbors=False),
        semantic_source=SemanticSource(tmp_path, reader=vault_reader, embedder=vault_reader._embedder),
        episodic_source=EpisodicSource(tmp_path, store=episodic_store, embedder=episodic_store.embedder),
    )

    output = tmp_path / "snapshot.json"
    path = service.export_snapshot(output_path=output, mode="semantic", use_cache=False)

    assert path.exists()
    assert '"mode":"semantic"' in path.read_text(encoding="utf-8").replace(" ", "")
