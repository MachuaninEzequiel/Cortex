from __future__ import annotations

from collections import Counter

from cortex.webgraph.config import WebGraphConfig
from cortex.webgraph.contracts import (
    EpisodicRecord,
    SemanticRecord,
    WebGraphEdge,
    WebGraphNode,
    WebGraphSnapshot,
    WebGraphStats,
)
from cortex.webgraph.relation_builder import RelationBuilder


class GraphBuilder:
    """Assemble the hybrid Cortex graph from semantic and episodic records."""

    def __init__(self, config: WebGraphConfig) -> None:
        self.config = config
        self.relation_builder = RelationBuilder(config)

    def build_snapshot(
        self,
        *,
        fingerprint: str,
        mode: str,
        semantic_records: list[SemanticRecord],
        episodic_records: list[EpisodicRecord],
    ) -> WebGraphSnapshot:
        if mode == "semantic":
            episodic_records = []
        elif mode == "episodic":
            semantic_records = []

        edges = self.relation_builder.build_edges(semantic_records, episodic_records)
        nodes = self._build_nodes(semantic_records, episodic_records, edges)
        visible_node_ids = {node.id for node in nodes}
        filtered_edges = [
            edge
            for edge in edges
            if edge.source in visible_node_ids and edge.target in visible_node_ids
        ]
        stats = WebGraphStats(
            node_count=len(nodes),
            edge_count=len(filtered_edges),
            mode=mode,  # type: ignore[arg-type]
            truncated=False,
        )
        return WebGraphSnapshot(
            fingerprint=fingerprint,
            mode=mode,  # type: ignore[arg-type]
            stats=stats,
            nodes=nodes,
            edges=filtered_edges,
        )

    @staticmethod
    def _build_nodes(
        semantic_records: list[SemanticRecord],
        episodic_records: list[EpisodicRecord],
        edges: list[WebGraphEdge],
    ) -> list[WebGraphNode]:
        degree_counter: Counter[str] = Counter()
        for edge in edges:
            degree_counter[edge.source] += 1
            degree_counter[edge.target] += 1

        nodes: list[WebGraphNode] = []
        for record in semantic_records:
            nodes.append(
                WebGraphNode(
                    id=record.node_id,
                    node_type=record.node_type,
                    source="semantic",
                    label=record.title,
                    summary=record.summary,
                    rel_path=record.rel_path,
                    tags=list(record.tags),
                    degree=degree_counter.get(record.node_id, 0),
                    metadata={"abs_path": record.abs_path},
                )
            )

        for record in episodic_records:
            nodes.append(
                WebGraphNode(
                    id=record.node_id,
                    node_type=record.node_type,
                    source="episodic",
                    label=record.label,
                    summary=record.summary,
                    memory_id=record.memory_id,
                    tags=list(record.tags),
                    files=list(record.files),
                    timestamp=record.timestamp,
                    degree=degree_counter.get(record.node_id, 0),
                    metadata=dict(record.metadata),
                )
            )

        return sorted(nodes, key=lambda node: (node.source, node.node_type, node.label.lower()))

