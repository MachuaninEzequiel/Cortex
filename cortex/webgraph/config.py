from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from cortex.webgraph.contracts import WebGraphMode


class WebGraphConfig(BaseModel):
    server_host: str = "127.0.0.1"
    server_port: int = 8765
    auto_open_browser: bool = True
    default_mode: WebGraphMode = "hybrid"
    semantic_neighbor_threshold: float = Field(default=0.82, ge=0.0, le=1.0)
    semantic_neighbor_max_edges_per_node: int = Field(default=2, ge=0)
    semantic_neighbor_max_nodes: int = Field(default=220, ge=0)
    enable_semantic_neighbors: bool = True
    max_subgraph_depth: int = Field(default=2, ge=1, le=5)
    ignored_tags: list[str] = Field(default_factory=lambda: ["release-2", "general"])

    @classmethod
    def default_path(cls, project_root: Path | None = None) -> Path:
        root = project_root or Path.cwd()
        return root / ".cortex" / "webgraph" / "config.yaml"

    @classmethod
    def load(cls, project_root: Path | None = None) -> "WebGraphConfig":
        path = cls.default_path(project_root)
        if not path.exists():
            return cls()
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls.model_validate(data)

    def save(self, project_root: Path | None = None) -> Path:
        path = self.default_path(project_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(self.model_dump(), sort_keys=False), encoding="utf-8")
        return path

