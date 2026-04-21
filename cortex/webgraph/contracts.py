from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

WebGraphMode = Literal["semantic", "episodic", "hybrid"]


class WebGraphCapabilities(BaseModel):
    filters: bool = True
    subgraph: bool = True
    open_file: bool = True
    relation_explanations: bool = True


class WebGraphStats(BaseModel):
    node_count: int = 0
    edge_count: int = 0
    mode: WebGraphMode = "hybrid"
    truncated: bool = False


class WebGraphNode(BaseModel):
    id: str
    node_type: str
    source: Literal["semantic", "episodic"]
    label: str
    summary: str = ""
    rel_path: str | None = None
    memory_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
    timestamp: str | None = None
    degree: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class WebGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    edge_type: str
    weight: float = 1.0
    evidence: list[str] = Field(default_factory=list)


class WebGraphSnapshot(BaseModel):
    version: str = "2.0"
    fingerprint: str
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    mode: WebGraphMode = "hybrid"
    stats: WebGraphStats
    capabilities: WebGraphCapabilities = Field(default_factory=WebGraphCapabilities)
    nodes: list[WebGraphNode] = Field(default_factory=list)
    edges: list[WebGraphEdge] = Field(default_factory=list)


class WebGraphNodeDetail(BaseModel):
    node: WebGraphNode
    relations: list[WebGraphEdge] = Field(default_factory=list)
    neighbors: list[WebGraphNode] = Field(default_factory=list)


class SemanticRecord(BaseModel):
    node_id: str
    node_type: str
    title: str
    summary: str
    rel_path: str
    abs_path: str
    tags: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    content: str = ""
    embedding: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EpisodicRecord(BaseModel):
    node_id: str
    node_type: str
    label: str
    summary: str
    memory_id: str
    tags: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
    timestamp: str | None = None
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding: list[float] | None = None

