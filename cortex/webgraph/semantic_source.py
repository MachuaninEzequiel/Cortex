from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from cortex.episodic.embedder import Embedder
from cortex.semantic.vault_reader import VaultReader
from cortex.webgraph.contracts import SemanticRecord
from cortex.workspace.layout import WorkspaceLayout


def _read_project_config(project_root: Path, *, workspace_layout: WorkspaceLayout | None = None) -> dict[str, Any]:
    layout = workspace_layout or WorkspaceLayout.discover(project_root)
    config_path = layout.config_path
    if not config_path.exists():
        return {}
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def _normalize_summary(text: str, max_chars: int = 220) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 1].rstrip() + "…"


def _semantic_node_type(rel_path: str, tags: list[str]) -> str:
    rel_lower = rel_path.replace("\\", "/").lower()
    tag_set = {tag.lower() for tag in tags}
    if "spec" in tag_set or rel_lower.startswith("specs/"):
        return "semantic_spec"
    if "session" in tag_set or rel_lower.startswith("sessions/"):
        return "semantic_session"
    return "semantic_doc"


def _doc_type_from_rel_path(rel_path: str) -> str | None:
    """Best-effort DocType slug from the relative path inside the vault.

    Thin wrapper over the canonical ``infer_doc_type_from_path`` (Fase 13);
    kept for API compatibility with existing callers in this module.
    """
    from cortex.documentation.doc_type import infer_doc_type_from_path
    dt = infer_doc_type_from_path(rel_path)
    return dt.value if dt else None


class SemanticSource:
    """Adapter that projects VaultReader documents into webgraph records."""

    def __init__(
        self,
        project_root: Path | None = None,
        *,
        vault_path: Path | None = None,
        reader: VaultReader | None = None,
        embedder: Any | None = None,
        workspace_layout: WorkspaceLayout | None = None,
    ) -> None:
        self.project_root = project_root or Path.cwd()
        self._layout = workspace_layout or WorkspaceLayout.discover(self.project_root)
        self._runtime_config = _read_project_config(self.project_root, workspace_layout=self._layout)
        episodic_cfg = self._runtime_config.get("episodic", {})
        semantic_cfg = self._runtime_config.get("semantic", {})
        configured_vault_path = semantic_cfg.get("vault_path", "vault")
        self.vault_path = (
            vault_path.resolve()
            if vault_path is not None
            else self._layout.resolve_workspace_relative(configured_vault_path)
        )
        self.reader = reader or VaultReader(
            vault_path=str(self.vault_path),
            embedding_model=episodic_cfg.get("embedding_model", "all-MiniLM-L6-v2"),
            embedding_backend=episodic_cfg.get("embedding_backend", "onnx"),
        )
        self.embedder = embedder or Embedder(
            model_name=episodic_cfg.get("embedding_model", "all-MiniLM-L6-v2"),
            backend=episodic_cfg.get("embedding_backend", "onnx"),
        )

    def load_records(self, *, include_embeddings: bool = True) -> list[SemanticRecord]:
        from cortex.webgraph.style import style_for_doc_type
        records: list[SemanticRecord] = []
        for rel_path, doc in self.reader.iter_documents():
            rel_posix = rel_path.replace("\\", "/")
            node_type = _semantic_node_type(rel_posix, doc.tags)
            search_text = f"{doc.title} {doc.content}".strip()
            doc_type_slug = _doc_type_from_rel_path(rel_posix)
            style = style_for_doc_type(doc_type_slug)
            metadata: dict[str, Any] = {
                "path": rel_posix,
                "doc_type": doc_type_slug,
                "vault_scope": getattr(doc, "origin_scope", "local") or "local",
                "color": style.color,
                "shape": style.shape,
            }
            origin_project = getattr(doc, "origin_project_id", None)
            if origin_project:
                metadata["origin_project_id"] = origin_project
            records.append(
                SemanticRecord(
                    node_id=f"semantic:{rel_posix}",
                    node_type=node_type,
                    title=doc.title,
                    summary=_normalize_summary(doc.content),
                    rel_path=rel_posix,
                    abs_path=str(Path(doc.path).resolve()),
                    tags=list(doc.tags),
                    links=list(doc.links),
                    content=doc.content,
                    embedding=self.embedder.embed(search_text) if include_embeddings else None,
                    metadata=metadata,
                )
            )
        return records
