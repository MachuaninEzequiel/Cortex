"""Contexto de servicios para las acciones del catálogo (Obra 05 Fase B).

Regla dura #1 del contrato: toda acción delega en su servicio. El
``ActionContext`` agrupa esas dependencias con carga PEREZOSA — el gate
de ``cortex next`` es <2s en repo mediano, así que nada pesado (ChromaDB,
ONNX) se construye salvo que una acción lo necesite realmente.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cortex.workspace.layout import WorkspaceLayout


@dataclass
class ActionContext:
    layout: WorkspaceLayout
    _mem: object | None = field(default=None, repr=False)
    _sessions: object | None = field(default=None, repr=False)

    @classmethod
    def from_project_root(cls, project_root: Path | None = None) -> "ActionContext":
        start = (
            Path(project_root).expanduser().resolve()
            if project_root
            else Path.cwd().resolve()
        )
        layout = WorkspaceLayout.discover(start)
        return cls(layout=layout)

    @property
    def dot_cortex(self) -> Path:
        """Directorio ``.cortex`` real (workspace_root ya lo es en layout nuevo;
        en legacy workspace_root == repo_root, ahí sí se agrega el nivel)."""
        ws = self.layout.workspace_root
        return ws if ws.name == ".cortex" else ws / ".cortex"

    @property
    def vault_path(self) -> Path:
        vp = Path(self.layout.vault_path)
        return vp if vp.is_absolute() else self.layout.workspace_root / vp

    def config_existe(self) -> bool:
        return self.layout.config_path.exists()

    # ── carga perezosa de servicios ─────────────────────────────────

    @property
    def mem(self):
        if self._mem is None:
            from cortex.core import AgentMemory

            self._mem = AgentMemory(config_path=self.layout.config_path)
        return self._mem

    @property
    def sessions(self):
        if self._sessions is None:
            from cortex.session.service import SessionService
            from cortex.session.storage import SessionStorage

            self._sessions = SessionService(
                storage=SessionStorage(sessions_dir=self.dot_cortex / "sessions"),
                repo_root=self.layout.workspace_root,
            )
        return self._sessions
