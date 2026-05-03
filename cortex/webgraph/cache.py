from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cortex.webgraph.contracts import WebGraphSnapshot
from cortex.workspace.layout import WorkspaceLayout


class WebGraphCache:
    """Persistent snapshot cache for the hybrid webgraph."""

    def __init__(self, project_root: Path, *, workspace_layout: WorkspaceLayout | None = None) -> None:
        self.project_root = project_root
        self._layout = workspace_layout or WorkspaceLayout.discover(project_root)
        self.cache_dir = self._layout.webgraph_cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def snapshot_path(self, mode: str) -> Path:
        return self.cache_dir / f"snapshot-{mode}.json"

    def meta_path(self) -> Path:
        return self.cache_dir / "meta.json"

    def load_snapshot(self, mode: str, fingerprint: str) -> WebGraphSnapshot | None:
        path = self.snapshot_path(mode)
        meta_path = self.meta_path()
        if not path.exists() or not meta_path.exists():
            return None
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get(mode) != fingerprint:
            return None
        return WebGraphSnapshot.model_validate_json(path.read_text(encoding="utf-8"))

    def store_snapshot(self, mode: str, snapshot: WebGraphSnapshot) -> Path:
        path = self.snapshot_path(mode)
        path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
        meta_path = self.meta_path()
        meta: dict[str, Any] = {}
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta[mode] = snapshot.fingerprint
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return path

    def compute_fingerprint(
        self,
        *,
        vault_path: Path,
        episodic_path: Path,
        episodic_count: int,
        episodic_cache_token: int,
        config_payload: dict[str, Any],
    ) -> str:
        hasher = hashlib.sha256()
        hasher.update(json.dumps(config_payload, sort_keys=True).encode("utf-8"))
        self._hash_tree(hasher, vault_path)
        self._hash_tree(hasher, episodic_path)
        hasher.update(str(episodic_count).encode("utf-8"))
        hasher.update(str(episodic_cache_token).encode("utf-8"))
        return hasher.hexdigest()

    @staticmethod
    def _hash_tree(hasher: hashlib._Hash, root: Path) -> None:
        if not root.exists():
            hasher.update(f"missing:{root}".encode())
            return
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            stat = path.stat()
            hasher.update(str(path.relative_to(root)).encode("utf-8"))
            hasher.update(str(int(stat.st_mtime_ns)).encode("utf-8"))
            hasher.update(str(stat.st_size).encode("utf-8"))

