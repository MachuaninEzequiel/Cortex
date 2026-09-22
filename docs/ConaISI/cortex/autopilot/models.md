# cortex/autopilot/models.py

## Qué tiene adentro

- **Ruta de código:** `cortex/autopilot/models.py` (85 líneas).
- **Módulo Python:** `cortex.autopilot.models`.
- **Docstring del módulo:** cortex.autopilot.models — Domain models for detectors and policies.
- **Clases definidas:**
  - `DetectionRequest` (BaseModel)
    - Input to the detector pipeline.
  - `DetectionResult` (BaseModel)
    - Output of ``resolve_detectors``.
  - `PolicyDecision` (BaseModel)
    - Legacy Pydantic model preserved for tests still using the old protocol.
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.autopilot.models — Domain models for detectors and policies.

Phase 03 deleted the parallel session-lifecycle models that used to live
here (``AutopilotSessionState``, ``AutopilotCheckpoint``, ``AutopilotEvent``,
``SessionDraft``, ``AutopilotBudgetSnapshot``, ``HookSessionStartOutput``).
Their roles are now played by :mod:`cortex.session.models`
(``SessionRecord``, ``Checkpoint``) and the documenter's session-note
writers.

What remains here is the **decision-layer vocabulary**: the structured
inputs/outputs of the detector and policy primitives that still belong to
the Autopilot module.

Phase 04 cleanup completed the deletion of ``HookSessionStartOutput`` —
the legacy ``cortex/autopilot/hooks/`` scripts and adapters that consumed
it have been retired in favour of ``cortex/session/hooks/``.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `__future__`, `typing`, `pydantic`

### Envía a

- `cortex.autopilot.detectors.ambiguous`
- `cortex.autopilot.detectors.base`
- `cortex.autopilot.detectors.default`
- `cortex.autopilot.lifecycle`
- `cortex.autopilot.service`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 85.

---
Fuente: código de `cortex/autopilot/models.py` (AST + grafo de imports internos). No se usó documentación previa.
