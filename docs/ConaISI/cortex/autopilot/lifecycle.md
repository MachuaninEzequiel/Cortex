# cortex/autopilot/lifecycle.py

## Qué tiene adentro

- **Ruta de código:** `cortex/autopilot/lifecycle.py` (154 líneas).
- **Módulo Python:** `cortex.autopilot.lifecycle`.
- **Docstring del módulo:** cortex.autopilot.lifecycle — Request/result types for AutopilotService.
- **Clases definidas:**
  - `AutopilotStartRequest` (BaseModel)
    - Adopt the currently-active session and apply the requested mode.
  - `AutopilotStartResult` (BaseModel)
    - Outcome of ``AutopilotService.start``.
  - `AutopilotPreflightRequest` (BaseModel)
  - `AutopilotPreflightResult` (BaseModel)
  - `AutopilotCheckpointRequest` (BaseModel)
    - Source/payload for a checkpoint to append to the active session.
  - `AutopilotCheckpointResult` (BaseModel)
  - `AutopilotFinishRequest` (BaseModel)
    - Close the active session.
  - `AutopilotFinishResult` (BaseModel)
  - `AutopilotStatusResult` (BaseModel)
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.autopilot.lifecycle — Request/result types for AutopilotService.

Phase 03 refactor: every model references the canonical
:class:`cortex.session.models.SessionRecord` instead of the now-deleted
``AutopilotSessionState``. ``preflight`` survives as a *dry-run* of the
detector pipeline (it no longer mutates a session — that responsibility
moved to ``cortex.session.SessionService``).

## Relaciones

### Recibe de

- `cortex.autopilot.models` (DetectionResult)
- `cortex.autopilot.policies` (AutopilotMode, AutopilotPolicy)
- `cortex.session.models` (Checkpoint, SessionRecord, SessionStatus)
- Dependencias externas/stdlib: `__future__`, `pydantic`

### Envía a

- `cortex.autopilot.cli`
- `cortex.autopilot.mcp_tools`
- `cortex.autopilot.service`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 154.

---
Fuente: código de `cortex/autopilot/lifecycle.py` (AST + grafo de imports internos). No se usó documentación previa.
