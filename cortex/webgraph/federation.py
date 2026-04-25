from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml

from cortex.webgraph.contracts import (
    WebGraphEdge,
    WebGraphMode,
    WebGraphNode,
    WebGraphNodeDetail,
    WebGraphSnapshot,
    WebGraphStats,
)
from cortex.webgraph.service import WebGraphService


@dataclass(frozen=True)
class WorkspaceProject:
    project_id: str
    root: Path


def load_workspace_projects(workspace_file: Path) -> list[WorkspaceProject]:
    payload = yaml.safe_load(workspace_file.read_text(encoding="utf-8")) or {}
    projects = payload.get("projects", [])
    if not isinstance(projects, list):
        return []

    loaded: list[WorkspaceProject] = []
    for item in projects:
        if not isinstance(item, dict):
            continue
        project_id = str(item.get("id", "")).strip()
        root_raw = str(item.get("root", "")).strip()
        if not project_id or not root_raw:
            continue
        root = Path(root_raw).expanduser().resolve()
        loaded.append(WorkspaceProject(project_id=project_id, root=root))
    return loaded


class FederatedWebGraphService:
    """Compose a unified snapshot from multiple project roots."""

    def __init__(self, workspace_file: Path) -> None:
        self.workspace_file = workspace_file.resolve()
        self.projects = load_workspace_projects(self.workspace_file)
        self._services: dict[str, WebGraphService] = {
            project.project_id: WebGraphService(project.root)
            for project in self.projects
        }

    def build_snapshot(self, mode: WebGraphMode = "hybrid", *, use_cache: bool = True) -> WebGraphSnapshot:
        del use_cache
        nodes: list[WebGraphNode] = []
        edges: list[WebGraphEdge] = []
        fingerprints: list[str] = []

        for project_id, service in self._services.items():
            snapshot = service.build_snapshot(mode=mode, use_cache=True)
            fingerprints.append(f"{project_id}:{snapshot.fingerprint}")

            for node in snapshot.nodes:
                prefixed_id = self._prefixed(project_id, node.id)
                metadata = dict(node.metadata)
                metadata["project_id"] = project_id
                nodes.append(
                    node.model_copy(
                        update={
                            "id": prefixed_id,
                            "metadata": metadata,
                        }
                    )
                )

            for edge in snapshot.edges:
                edges.append(
                    edge.model_copy(
                        update={
                            "id": self._prefixed(project_id, edge.id),
                            "source": self._prefixed(project_id, edge.source),
                            "target": self._prefixed(project_id, edge.target),
                        }
                    )
                )

        digest = hashlib.sha256("|".join(sorted(fingerprints)).encode("utf-8")).hexdigest()
        return WebGraphSnapshot(
            fingerprint=digest,
            mode=mode,
            stats=WebGraphStats(
                node_count=len(nodes),
                edge_count=len(edges),
                mode=mode,
                truncated=False,
            ),
            nodes=nodes,
            edges=edges,
        )

    def export_snapshot(
        self,
        output_path: Path | None = None,
        *,
        mode: WebGraphMode = "hybrid",
        use_cache: bool = True,
    ) -> Path:
        snapshot = self.build_snapshot(mode=mode, use_cache=use_cache)
        default_path = self.workspace_file.parent / ".cortex" / "webgraph" / f"federated-snapshot-{mode}.json"
        path = output_path or default_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
        return path

    def get_node_detail(self, node_id: str, *, mode: WebGraphMode = "hybrid") -> WebGraphNodeDetail:
        snapshot = self.build_snapshot(mode=mode, use_cache=True)
        nodes_by_id = {node.id: node for node in snapshot.nodes}
        node = nodes_by_id[node_id]
        relations = [edge for edge in snapshot.edges if edge.source == node_id or edge.target == node_id]
        neighbor_ids = {
            edge.target if edge.source == node_id else edge.source
            for edge in relations
        }
        neighbors = [nodes_by_id[item_id] for item_id in sorted(neighbor_ids) if item_id in nodes_by_id]
        return WebGraphNodeDetail(node=node, relations=relations, neighbors=neighbors)

    def get_subgraph(
        self,
        node_id: str,
        *,
        depth: int = 1,
        mode: WebGraphMode = "hybrid",
        edge_types: set[str] | None = None,
    ) -> WebGraphSnapshot:
        # Reuse single-graph implementation behavior by filtering from full snapshot.
        snapshot = self.build_snapshot(mode=mode, use_cache=True)
        if depth <= 0:
            return snapshot.model_copy(update={"nodes": [], "edges": []})

        adjacency: dict[str, set[str]] = {}
        for edge in snapshot.edges:
            if edge_types and edge.edge_type not in edge_types:
                continue
            adjacency.setdefault(edge.source, set()).add(edge.target)
            adjacency.setdefault(edge.target, set()).add(edge.source)

        frontier = {node_id}
        visited = {node_id}
        for _ in range(depth):
            new_frontier: set[str] = set()
            for current in frontier:
                for neighbor in adjacency.get(current, set()):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        new_frontier.add(neighbor)
            frontier = new_frontier
            if not frontier:
                break

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

    def resolve_node_path(self, node_id: str, *, mode: WebGraphMode = "hybrid") -> Path | None:
        project_id, raw_id = self._split_prefixed(node_id)
        service = self._services.get(project_id)
        if service is None:
            return None
        return service.resolve_node_path(raw_id, mode=mode)

    @staticmethod
    def _prefixed(project_id: str, item_id: str) -> str:
        return f"{project_id}::{item_id}"

    @staticmethod
    def _split_prefixed(value: str) -> tuple[str, str]:
        if "::" not in value:
            return "", value
        project_id, raw_id = value.split("::", 1)
        return project_id, raw_id

