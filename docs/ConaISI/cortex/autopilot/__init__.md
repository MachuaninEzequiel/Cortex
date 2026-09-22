# cortex/autopilot/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/autopilot/__init__.py` (34 líneas).
- **Módulo Python:** `cortex.autopilot`.
- **Docstring del módulo:** cortex.autopilot — Policy + hooks layer over the cortex.session primitive.
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.autopilot — Policy + hooks layer over the cortex.session primitive.

Phase 03 of the Pluggable Middle architecture turned this module from a
parallel session-lifecycle implementation into a *thin orchestrator* that
applies an :class:`AutopilotPolicy` over the canonical
:class:`cortex.session.service.SessionService`.

Public API:
    :class:`AutopilotService`  — entry point, factory ``from_project_root``.
    :class:`AutopilotMode`     — observe / assist / autopilot.
    :class:`AutopilotPolicy`   — declarative policy (frozen dataclass).
    :class:`PolicyEnforcer`    — evaluates the policy at lifecycle hooks.

## Relaciones

### Recibe de

- `cortex.autopilot.policies` (AutopilotMode, AutopilotPolicy, EnforcementResult, EnforcementSeverity, PolicyEnforcer)
- `cortex.autopilot.service` (AutopilotService)
- Dependencias externas/stdlib: `__future__`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 34.
Reexportes observados:
- cortex.autopilot.policies: AutopilotMode, AutopilotPolicy, EnforcementResult, EnforcementSeverity, PolicyEnforcer
- cortex.autopilot.service: AutopilotService

---
Fuente: código de `cortex/autopilot/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
