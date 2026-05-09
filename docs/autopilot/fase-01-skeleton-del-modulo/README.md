# Fase 1 - Skeleton del Modulo

**Fuente:** `docs/autopilot/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion de la fase

En esta fase se lleva a cabo lo definido en el plan global para `Fase 1 - Skeleton del Modulo`. El cuerpo operativo de la fase se copia directamente desde `docs/autopilot/README.md` para mantener la especificacion sin reinterpretaciones.

Al terminar la realizacion de esta fase, es obligatorio documentar lo desarrollado dentro de esta misma carpeta en un archivo `REALIZACION.md`. Esa realizacion debe incluir decisiones tomadas, archivos modificados, tests ejecutados, desviaciones respecto del plan, riesgos residuales y pendientes.

## Nota obligatoria para agentes implementadores

Esta nota baja a esta fase las reglas del item 18 del plan global. Es obligatoria antes de implementar.

### Reglas generales heredadas del item 18

- **No improvises.** Segui el alcance exacto de esta fase y no agregues campos, servicios ni adapters fuera de lo definido.
- **No saltees tests.** La fase no esta completa hasta cumplir su gate de salida.
- **Usa `WorkspaceLayout`.** No hardcodees `.cortex/`, `config.yaml`, `vault/` ni rutas legacy.
- **Cada archivo nuevo debe tener test unitario correspondiente** cuando la fase cree codigo runtime.
- **Si algo no esta claro, pregunta antes de asumir.** La racionalizacion es el enemigo del Autopilot.

### Aplicacion especifica en esta fase

- Usa los modelos exactos definidos en la seccion 17 del plan global. No inventes campos ni renombres clases.
- No toques el CLI existente en esta fase.
- No toques el MCP server en esta fase.
- El modulo debe poder importarse sin inicializar Chroma ni ONNX.

## Referencia obligatoria de la seccion 17

El item 18 del plan global exige usar los modelos exactos definidos en la seccion 17. Para esta fase, esta referencia forma parte del contrato operativo y no debe reinterpretarse.

### Detalle de `models.py` para el implementador

Este archivo debe contener TODOS los modelos base del sistema. Los modelos estan definidos a lo largo de este documento; aqui se consolidan para referencia del implementador:

```python
"""cortex.autopilot.models — Domain models for the Autopilot module."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field
import uuid


class AutopilotBudgetSnapshot(BaseModel):
    chars_injected: int = 0
    items_retrieved: int = 0
    embeddings_used: bool = False
    subagents_spawned: int = 0
    deep_track_reason: str | None = None


class AutopilotCheckpoint(BaseModel):
    timestamp: datetime
    summary: str
    files_at_checkpoint: list[str] = []
    verified: bool = False


class AutopilotSessionState(BaseModel):
    schema_version: int = 1
    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    project_root: str
    workspace_root: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    status: Literal[
        "started", "preflight_done", "implementation_seen",
        "documented", "finished", "failed",
    ] = "started"
    mode: Literal["observe", "assist", "autopilot"] = "assist"
    user_request: str | None = None
    title_hint: str | None = None
    detected_task_type: str | None = None
    complexity: Literal["none", "fast", "deep"] = "none"
    spec_path: str | None = None
    session_note_path: str | None = None
    changed_files: list[str] = []
    commands_seen: list[str] = []
    tools_seen: list[str] = []
    checkpoints: list[AutopilotCheckpoint] = []
    budget: AutopilotBudgetSnapshot = Field(
        default_factory=AutopilotBudgetSnapshot
    )
    warnings: list[str] = []


class AutopilotEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    session_id: str
    event_type: str  # "start", "preflight", "checkpoint", "finish", etc.
    source: Literal["cli", "mcp", "hook", "agent", "detector", "policy"]
    payload: dict[str, Any] = {}


class DetectionRequest(BaseModel):
    user_request: str | None = None
    changed_files: list[str] = []
    git_diff_stat: str | None = None
    session_state: AutopilotSessionState | None = None


class DetectionResult(BaseModel):
    task_type: Literal[
        "question-only", "docs-only", "fast-code",
        "deep-code", "security", "ambiguous", "noop"
    ]
    confidence: float = 0.0
    reason: str = ""
    suggested_complexity: Literal["none", "fast", "deep"] = "none"


class PolicyDecision(BaseModel):
    allowed: bool
    reason: str
    action: Literal["proceed", "warn", "degrade", "block"] = "proceed"
    degrade_to: Literal["observe", "assist", "fast"] | None = None


class SessionDraft(BaseModel):
    title: str
    body: str
    confidence: Literal["high", "medium", "auto-draft"] = "medium"
    warnings: list[str] = []
    source_events: int = 0


class HookSessionStartOutput(BaseModel):
    session_id: str
    mode: Literal["observe", "assist", "autopilot"]
    bootstrap_content: str
    budget_profile: str
    available_tools: list[str] = []
    cortex_version: str = ""


class DelegationResult(BaseModel):
    task_id: str
    status: Literal["completed", "failed", "rejected"]
    diff_summary: str = ""
    files_changed: list[str] = []
    tests_passed: bool | None = None
    spec_path: str | None = None
    rejection_reason: str | None = None
```

### Detalle de `state_store.py` para el implementador

```python
"""cortex.autopilot.state_store — Persistent state for Autopilot sessions."""
from pathlib import Path
import json
from .models import AutopilotSessionState, AutopilotEvent


class StateStore:
    """JSON/JSONL persistence for Autopilot state.

    Directory layout:
        .cortex/run/autopilot/sessions/<session-id>.json
        .cortex/run/autopilot/events/<session-id>.jsonl
    """

    def __init__(self, workspace_root: Path) -> None:
        self.root = workspace_root / "run" / "autopilot"
        self.sessions_dir = self.root / "sessions"
        self.events_dir = self.root / "events"

    def _ensure_dirs(self) -> None:
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.events_dir.mkdir(parents=True, exist_ok=True)

    def save_state(self, state: AutopilotSessionState) -> Path:
        self._ensure_dirs()
        path = self.sessions_dir / f"{state.session_id}.json"
        path.write_text(
            state.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return path

    def load_state(self, session_id: str) -> AutopilotSessionState | None:
        path = self.sessions_dir / f"{session_id}.json"
        if not path.exists():
            return None
        return AutopilotSessionState.model_validate_json(
            path.read_text(encoding="utf-8")
        )

    def append_event(self, event: AutopilotEvent) -> None:
        self._ensure_dirs()
        path = self.events_dir / f"{event.session_id}.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")

    def load_events(self, session_id: str) -> list[AutopilotEvent]:
        path = self.events_dir / f"{session_id}.jsonl"
        if not path.exists():
            return []
        events = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(AutopilotEvent.model_validate_json(line))
        return events

    def list_sessions(self) -> list[str]:
        if not self.sessions_dir.exists():
            return []
        return [
            p.stem for p in self.sessions_dir.glob("*.json")
        ]
```

## Plan operativo original

## Fase 1 - Skeleton del Modulo

### Objetivo

Crear el paquete `cortex.autopilot` sin comportamiento invasivo.

### Archivos a crear

```text
cortex/autopilot/__init__.py
cortex/autopilot/models.py
cortex/autopilot/config.py
cortex/autopilot/state_store.py
cortex/autopilot/registry.py
cortex/autopilot/errors.py
tests/unit/autopilot/test_models.py
tests/unit/autopilot/test_state_store.py
```

### Responsabilidades

`models.py`

- Define estado, eventos, checkpoints, budget snapshot, decisions.

`config.py`

- Carga config opcional desde `.cortex/autopilot.yaml`.
- Provee defaults si no existe.

`state_store.py`

- Lee/escribe JSON y JSONL.
- Usa `WorkspaceLayout`.
- Operaciones atomicas cuando sea posible.

`registry.py`

- Registro de detectors, policies, renderers y adapters.

### Criterios de diseno

- No importar MCP.
- No importar Typer.
- No importar adapters IDE.
- No llamar `AgentMemory` todavia.

### Checklist

- [ ] `AutopilotSessionState` serializa y deserializa.
- [ ] `StateStore.create_session()` genera un id estable.
- [ ] `StateStore.append_event()` escribe JSONL.
- [ ] `StateStore.load()` falla con error claro si no existe.
- [ ] Tests unitarios cubren new layout y legacy layout.

### Gate de salida

- `pytest tests/unit/autopilot` pasa.
- El modulo puede importarse sin inicializar Chroma ni ONNX.

---


