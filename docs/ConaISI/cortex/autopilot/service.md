# cortex/autopilot/service.py

## Qué tiene adentro

- **Ruta de código:** `cortex/autopilot/service.py` (445 líneas).
- **Módulo Python:** `cortex.autopilot.service`.
- **Docstring del módulo:** cortex.autopilot.service — AutopilotService over the Session primitive.
- **Clases definidas:**
  - `AutopilotService`
    - Apply an :class:`AutopilotPolicy` over a canonical session lifecycle.
    - Métodos públicos/especiales: `__init__`, `from_project_root`, `policy`, `session_service`, `start`, `preflight`, `checkpoint`, `finish`, `status`
    - Métodos internos: `_require_active`, `_resolve_target_session`, `_finish_manual`, `_finish_auto`
- **Funciones de módulo:**
  - `_default_detectors()`
  - `_warnings(results)`
  - `_policy_with_mode(policy, mode)` — Return a copy of ``policy`` with the mode replaced.
  - `_intent_to_status(intent)` — Translate a finish ``intent`` to a :class:`SessionStatus`.
  - `_intent_to_forced_status(intent)` — Translate a finish ``intent`` to a forced status override.
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.autopilot.service — AutopilotService over the Session primitive.

Phase 03 refactor: ``AutopilotService`` is now a thin orchestrator that
wires together:

    * :class:`cortex.session.service.SessionService` for lifecycle ops
      (the SessionRecord is the canonical state),
    * :class:`cortex.autopilot.policies.PolicyEnforcer` for warnings and
      blocks at lifecycle hooks,
    * :mod:`cortex.autopilot.detectors` for the dry-run *preflight*,
    * :mod:`cortex.documenter` when ``finish(auto=True)`` needs to close
      the session via the canonical documenter pipeline.

The service does **not** open sessions — that is the job of
``cortex_create_spec``. ``start`` adopts whatever session is currently
active and surfaces open-time policy warnings.

Public API kept for backwards-compatibility:
    :meth:`start`        — adopt the active session under the configured policy.
    :meth:`preflight`    — dry-run the detector pipeline.
    :meth:`checkpoint`   — append a checkpoint and surface policy warnings.
    :meth:`finish`       — close the active session (auto=True → documenter).
    :meth:`status`       — describe the active or named session.
    :classmethod:`from_project_root` — wire dependencies from a project root.

## Relaciones

### Recibe de

- `cortex.autopilot.config` (load_autopilot_config)
- `cortex.autopilot.detectors.ambiguous` (AmbiguousRequestDetector)
- `cortex.autopilot.detectors.base` (resolve_detectors)
- `cortex.autopilot.detectors.default` (CodeChangeDetector, DocsOnlyDetector, LargeRefactorDetector, NoopDetector, QuestionOnlyDetector, SecuritySensitiveDetector)
- `cortex.autopilot.errors` (AutopilotError, NoActiveSessionError)
- `cortex.autopilot.lifecycle` (AutopilotCheckpointRequest, AutopilotCheckpointResult, AutopilotFinishRequest, AutopilotFinishResult, AutopilotPreflightRequest, AutopilotPreflightResult, AutopilotStartRequest, AutopilotStartResult, AutopilotStatusResult)
- `cortex.autopilot.models` (DetectionRequest)
- `cortex.autopilot.policies` (AutopilotMode, AutopilotPolicy, EnforcementResult, EnforcementSeverity, PolicyEnforcer)
- `cortex.session.errors` (SessionNotFound)
- `cortex.session.models` (CheckpointSource, SessionRecord, SessionStatus)
- `cortex.session.service` (SessionService)
- `cortex.session.storage` (SessionStorage)
- `cortex.workspace.layout` (WorkspaceLayout)
- Dependencias externas/stdlib: `logging`, `__future__`, `collections.abc`, `pathlib`, `typing`

### Envía a

- `cortex.autopilot`
- `cortex.autopilot.cli`
- `cortex.autopilot.doctor`
- `cortex.autopilot.mcp_tools`
- `cortex.mcp.server`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 445.
Docstrings de símbolos públicos:
- `AutopilotService.from_project_root`: Wire a service with workspace-discovered defaults.
- `AutopilotService.start`: Adopt the active session under the (optionally overridden) mode.
- `AutopilotService.preflight`: Run the detector pipeline against the request without touching state.
- `AutopilotService.checkpoint`: Append a checkpoint to the active session and surface warnings.
- `AutopilotService.finish`: Close the session, optionally via the documenter pipeline.
- `AutopilotService.status`: Describe the session.

---
Fuente: código de `cortex/autopilot/service.py` (AST + grafo de imports internos). No se usó documentación previa.
