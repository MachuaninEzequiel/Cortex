from __future__ import annotations

from collections import deque
from pathlib import Path

from cortex.runtime_context import slugify
from cortex.enterprise.config import discover_enterprise_config_path, load_enterprise_config
from cortex.webgraph.cache import WebGraphCache
from cortex.webgraph.config import WebGraphConfig
from cortex.webgraph.contracts import WebGraphEdge, WebGraphMode, WebGraphNode, WebGraphNodeDetail, WebGraphSnapshot
from cortex.webgraph.episodic_source import EpisodicSource
from cortex.webgraph.graph_builder import GraphBuilder
from cortex.webgraph.semantic_source import SemanticSource
from cortex.workspace.layout import WorkspaceLayout


class WebGraphService:
    """High-level orchestration for building and querying Cortex webgraph snapshots."""

    def __init__(
        self,
        project_root: Path | None = None,
        *,
        config: WebGraphConfig | None = None,
        vault_path: Path | None = None,
        persist_dir: Path | None = None,
        semantic_source: SemanticSource | None = None,
        episodic_source: EpisodicSource | None = None,
        workspace_layout: WorkspaceLayout | None = None,
    ) -> None:
        self.project_root = (project_root or Path.cwd()).resolve()
        self._layout = workspace_layout or WorkspaceLayout.discover(self.project_root)
        self.config = config or WebGraphConfig.load(self.project_root, workspace_layout=self._layout)
        self.semantic_source = semantic_source or SemanticSource(self.project_root, vault_path=vault_path)
        self.episodic_source = episodic_source or EpisodicSource(self.project_root, persist_dir=persist_dir)
        self.cache = WebGraphCache(self.project_root, workspace_layout=self._layout)
        self.graph_builder = GraphBuilder(self.config)

    def build_snapshot(
        self,
        mode: WebGraphMode = "hybrid",
        *,
        use_cache: bool = True,
        scope: str | None = None,
    ) -> WebGraphSnapshot:
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
        project_id = slugify(self.project_root.name, fallback="project")
        snapshot = snapshot.model_copy(
            update={
                "nodes": [
                    node.model_copy(
                        update={"metadata": {"project_id": project_id, "scope": "local", **dict(node.metadata)}}
                    )
                    for node in snapshot.nodes
                ]
            }
        )

        snapshot = _append_enterprise_nodes(snapshot, self.project_root, project_id=project_id, workspace_layout=self._layout)
        snapshot = _filter_snapshot_by_scope(snapshot, scope)
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

    def resolve_node_path(self, node_id: str, *, mode: WebGraphMode = "hybrid") -> Path | None:
        detail = self.get_node_detail(node_id, mode=mode)
        rel_path = detail.node.rel_path
        if not rel_path:
            return None
        return (self.semantic_source.vault_path / rel_path).resolve()

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


def _append_enterprise_nodes(snapshot: WebGraphSnapshot, project_root: Path, *, project_id: str, workspace_layout: WorkspaceLayout | None = None) -> WebGraphSnapshot:
    layout = workspace_layout or WorkspaceLayout.discover(project_root)
    org_path = discover_enterprise_config_path(project_root, workspace_layout=layout)
    if org_path is None:
        return snapshot
    try:
        cfg = load_enterprise_config(project_root, required=True, path=org_path, workspace_layout=layout)
    except Exception:
        return snapshot
    if cfg is None:
        return snapshot

    org_node_id = "enterprise:org"
    proj_node_id = "enterprise:project"
    vault_node_id = "enterprise:vault"

    enterprise_nodes: list[WebGraphNode] = [
        WebGraphNode(
            id=org_node_id,
            node_type="enterprise_org",
            source="semantic",
            label=cfg.organization.name,
            summary=f"profile={cfg.organization.profile}, slug={cfg.organization.slug}",
            metadata={"project_id": project_id, "scope": "enterprise"},
        ),
        WebGraphNode(
            id=proj_node_id,
            node_type="enterprise_project",
            source="semantic",
            label=project_root.name,
            summary=str(project_root),
            metadata={"project_id": project_id, "scope": "enterprise"},
        ),
    ]

    enterprise_edges: list[WebGraphEdge] = [
        WebGraphEdge(
            id="enterprise:org->project",
            source=org_node_id,
            target=proj_node_id,
            edge_type="enterprise_owns_project",
            weight=1.0,
        ),
    ]

    vault_path = cfg.resolve_enterprise_vault_path(project_root, workspace_root=layout.workspace_root)
    if vault_path is not None:
        enterprise_nodes.append(
            WebGraphNode(
                id=vault_node_id,
                node_type="enterprise_vault",
                source="semantic",
                label=vault_path.name,
                summary=str(vault_path),
                rel_path=None,
                metadata={"project_id": project_id, "scope": "enterprise"},
            )
        )
        enterprise_edges.append(
            WebGraphEdge(
                id="enterprise:org->vault",
                source=org_node_id,
                target=vault_node_id,
                edge_type="enterprise_vault",
                weight=1.0,
            )
        )

    # Avoid duplicates if called multiple times.
    existing_ids = {n.id for n in snapshot.nodes}
    nodes = snapshot.nodes + [n for n in enterprise_nodes if n.id not in existing_ids]

    existing_edge_ids = {e.id for e in snapshot.edges}
    edges = snapshot.edges + [e for e in enterprise_edges if e.id not in existing_edge_ids]

    return snapshot.model_copy(
        update={
            "nodes": nodes,
            "edges": edges,
            "stats": snapshot.stats.model_copy(update={"node_count": len(nodes), "edge_count": len(edges)}),
        }
    )


def _filter_snapshot_by_scope(snapshot: WebGraphSnapshot, scope: str | None) -> WebGraphSnapshot:
    if scope is None or scope == "all":
        return snapshot
    if scope not in {"local", "enterprise"}:
        return snapshot

    allowed_ids = {
        n.id
        for n in snapshot.nodes
        if str(n.metadata.get("scope", "local")).strip().lower() == scope
    }
    nodes = [n for n in snapshot.nodes if n.id in allowed_ids]
    edges = [e for e in snapshot.edges if e.source in allowed_ids and e.target in allowed_ids]
    return snapshot.model_copy(
        update={
            "nodes": nodes,
            "edges": edges,
            "stats": snapshot.stats.model_copy(update={"node_count": len(nodes), "edge_count": len(edges)}),
        }
    )
