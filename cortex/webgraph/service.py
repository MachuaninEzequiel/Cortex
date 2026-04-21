from __future__ import annotations

from collections import deque
from pathlib import Path

from cortex.webgraph.cache import WebGraphCache
from cortex.webgraph.config import WebGraphConfig
from cortex.webgraph.contracts import WebGraphMode, WebGraphNodeDetail, WebGraphSnapshot
from cortex.webgraph.episodic_source import EpisodicSource
from cortex.webgraph.graph_builder import GraphBuilder
from cortex.webgraph.semantic_source import SemanticSource


class WebGraphService:
    """High-level orchestration for building and querying Cortex webgraph snapshots."""

    def __init__(
        self,
        project_root: Path | None = None,
        *,
        config: WebGraphConfig | None = None,
        semantic_source: SemanticSource | None = None,
        episodic_source: EpisodicSource | None = None,
    ) -> None:
        self.project_root = project_root or Path.cwd()
        self.config = config or WebGraphConfig.load(self.project_root)
        self.semantic_source = semantic_source or SemanticSource(self.project_root)
        self.episodic_source = episodic_source or EpisodicSource(self.project_root)
        self.cache = WebGraphCache(self.project_root)
        self.graph_builder = GraphBuilder(self.config)

    def build_snapshot(self, mode: WebGraphMode = "hybrid", *, use_cache: bool = True) -> WebGraphSnapshot:
        fingerprint = self.cache.compute_fingerprint(
            vault_path=self.semantic_source.vault_path,
            episodic_path=self.episodic_source.persist_dir,
            episodic_count=self.episodic_source.store.count(),
            episodic_cache_token=self.episodic_source.store.cache_token,
            config_payload=self.config.model_dump(),
        )
        if use_cache:
            cached = self.cache.load_snapshot(mode, fingerprint)
            if cached is not None:
                return cached

        include_embeddings = mode == "hybrid"
        semantic_records = self.semantic_source.load_records(include_embeddings=include_embeddings)
        episodic_records = self.episodic_source.load_records(include_embeddings=include_embeddings)
        snapshot = self.graph_builder.build_snapshot(
            fingerprint=fingerprint,
            mode=mode,
            semantic_records=semantic_records,
            episodic_records=episodic_records,
        )
        self.cache.store_snapshot(mode, snapshot)
        return snapshot

    def export_snapshot(
        self,
        output_path: Path | None = None,
        *,
        mode: WebGraphMode = "hybrid",
        use_cache: bool = True,
    ) -> Path:
        snapshot = self.build_snapshot(mode=mode, use_cache=use_cache)
        path = output_path or self.cache.snapshot_path(mode)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
        return path

    def get_node_detail(self, node_id: str, *, mode: WebGraphMode = "hybrid") -> WebGraphNodeDetail:
        snapshot = self.build_snapshot(mode=mode)
        nodes_by_id = {node.id: node for node in snapshot.nodes}
        node = nodes_by_id[node_id]
        relations = [edge for edge in snapshot.edges if edge.source == node_id or edge.target == node_id]
        neighbor_ids = {
            edge.target if edge.source == node_id else edge.source
            for edge in relations
        }
        neighbors = [nodes_by_id[neighbor_id] for neighbor_id in sorted(neighbor_ids) if neighbor_id in nodes_by_id]
        return WebGraphNodeDetail(node=node, relations=relations, neighbors=neighbors)

    def get_subgraph(
        self,
        node_id: str,
        *,
        depth: int = 1,
        mode: WebGraphMode = "hybrid",
        edge_types: set[str] | None = None,
    ) -> WebGraphSnapshot:
        snapshot = self.build_snapshot(mode=mode)
        adjacency: dict[str, list[tuple[str, str]]] = {}
        for edge in snapshot.edges:
            if edge_types and edge.edge_type not in edge_types:
                continue
            adjacency.setdefault(edge.source, []).append((edge.target, edge.edge_type))
            adjacency.setdefault(edge.target, []).append((edge.source, edge.edge_type))

        visited = {node_id}
        queue: deque[tuple[str, int]] = deque([(node_id, 0)])
        while queue:
            current, current_depth = queue.popleft()
            if current_depth >= depth:
                continue
            for neighbor, _ in adjacency.get(current, []):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                queue.append((neighbor, current_depth + 1))

        nodes = [node for node in snapshot.nodes if node.id in visited]
        edges = [
            edge
            for edge in snapshot.edges
            if edge.source in visited and edge.target in visited
            and (not edge_types or edge.edge_type in edge_types)
        ]
        return snapshot.model_copy(
            update={
                "nodes": nodes,
                "edges": edges,
                "stats": snapshot.stats.model_copy(
                    update={"node_count": len(nodes), "edge_count": len(edges)},
                ),
            }
        )

