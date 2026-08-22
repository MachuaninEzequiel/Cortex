"""Contexto de servicios para las acciones del catálogo (Obra 05 Fase B).

Regla dura #1 del contrato: toda acción delega en su servicio. El
``ActionContext`` agrupa esas dependencias y se construye UNA vez por
invocación (``cortex next``, TUI home, etc.) — nunca por acción.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cortex.core import AgentMemory
from cortex.session.service import SessionService
from cortex.session.storage import SessionStorage
from cortex.workspace.layout import WorkspaceLayout


@dataclass
class ActionContext:
    mem: AgentMemory
    sessions: SessionService
    layout: WorkspaceLayout

    @classmethod
    def from_project_root(cls, project_root: Path | None = None) -> "ActionContext":
        start = (
            Path(project_root).expanduser().resolve()
            if project_root
            else Path.cwd().resolve()
        )
        layout = WorkspaceLayout.discover(start)
        config_path = layout.config_path
        if not config_path.exists():
            raise FileNotFoundError(
                f"Cortex no está configurado en {start} — no encuentro {config_path}"
            )

        mem = AgentMemory(config_path=config_path)
        sessions = SessionService(
            storage=SessionStorage(sessions_dir=layout.workspace_root / ".cortex" / "sessions"),
            repo_root=layout.workspace_root,
        )
        return cls(mem=mem, sessions=sessions, layout=layout)

    @property
    def dot_cortex(self) -> Path:
        return self.layout.workspace_root / ".cortex"
