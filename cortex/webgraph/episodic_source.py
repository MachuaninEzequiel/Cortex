from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from cortex.episodic.embedder import Embedder
from cortex.episodic.memory_store import EpisodicMemoryStore
from cortex.runtime_context import resolve_episodic_persist_dir
from cortex.webgraph.contracts import EpisodicRecord


def _read_project_config(project_root: Path) -> dict[str, Any]:
    config_path = project_root / "config.yaml"
    if not config_path.exists():
        return {}
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def _episodic_node_type(memory_type: str) -> str:
    normalized = memory_type.strip().lower()
    if normalized == "spec":
        return "episodic_spec"
    if normalized == "session":
        return "episodic_session"
    return "episodic_general"


def _normalize_summary(text: str, max_chars: int = 220) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 1].rstrip() + "…"


class EpisodicSource:
    """Adapter that projects episodic memory entries into webgraph records."""

    def __init__(
        self,
        project_root: Path | None = None,
        *,
        store: EpisodicMemoryStore | None = None,
        embedder: Any | None = None,
    ) -> None:
        self.project_root = project_root or Path.cwd()
        self._runtime_config = _read_project_config(self.project_root)
        episodic_cfg = self._runtime_config.get("episodic", {})
        self.persist_dir = resolve_episodic_persist_dir(self.project_root, episodic_cfg)
        self.store = store or EpisodicMemoryStore(
            persist_dir=str(self.persist_dir),
            collection_name=episodic_cfg.get("collection_name", "cortex_episodic"),
            embedding_model=episodic_cfg.get("embedding_model", "all-MiniLM-L6-v2"),
            embedding_backend=episodic_cfg.get("embedding_backend", "onnx"),
        )
        self.embedder = embedder or self.store.embedder or Embedder(
            model_name=episodic_cfg.get("embedding_model", "all-MiniLM-L6-v2"),
            backend=episodic_cfg.get("embedding_backend", "onnx"),
        )

    def load_records(self, *, include_embeddings: bool = True) -> list[EpisodicRecord]:
        records: list[EpisodicRecord] = []
        for entry in self.store.list_entries():
            records.append(
                EpisodicRecord(
                    node_id=f"episodic:{entry.id}",
                    node_type=_episodic_node_type(entry.memory_type),
                    label=entry.content.splitlines()[0][:120] or entry.id,
                    summary=_normalize_summary(entry.content),
                    memory_id=entry.id,
                    tags=list(entry.tags),
                    files=[file.replace("\\", "/") for file in entry.files],
                    timestamp=entry.timestamp.isoformat(),
                    content=entry.content,
                    metadata=dict(entry.metadata),
                    embedding=self.embedder.embed(entry.content) if include_embeddings else None,
                )
            )
        return records

