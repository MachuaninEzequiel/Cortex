# cortex/autopilot/policies.py

## Qué tiene adentro

- **Ruta de código:** `cortex/autopilot/policies.py` (374 líneas).
- **Módulo Python:** `cortex.autopilot.policies`.
- **Docstring del módulo:** cortex.autopilot.policies — Consolidated policy layer for the Autopilot module.
- **Clases definidas:**
  - `AutopilotMode` (StrEnum)
    - Operational stance of the Autopilot layer for a session.
  - `EnforcementSeverity` (StrEnum)
    - How strongly a policy enforcement signals its decision.
  - `EnforcementResult`
    - Outcome of one policy rule applied at a hook.
    - Métodos públicos/especiales: `allowed`, `proceed`, `warn`, `block`
  - `AutopilotPolicy`
    - Declarative policy applied to a Session under Autopilot supervision.
    - Métodos públicos/especiales: `from_config`
    - Métodos internos: `__post_init__`
  - `PolicyEnforcer`
    - Apply an :class:`AutopilotPolicy` at lifecycle hooks of a SessionRecord.
    - Métodos públicos/especiales: `__init__`, `policy`, `on_session_open`, `on_checkpoint`, `on_pre_close`
- **Funciones de módulo:**
  - `_looks_security_sensitive(text)`
  - `_has_verified_checkpoint(session)`
  - `_files_since_last_verified(session)` — Distinct artifact paths touched since the last verified checkpoint.
- **Constantes / símbolos de módulo:** `DEFAULT_BUDGET_PROFILE`, `KNOWN_BUDGET_PROFILES`, `_SECURITY_KEYWORDS`, `_SECURITY_KEYWORD_PATTERN`, `__all__`

## Para qué sirve

cortex.autopilot.policies — Consolidated policy layer for the Autopilot module.

Replaces the previous ``cortex.autopilot.policies.{base,default,auto_checkpoint}``
subpackage with a single module designed for the post-Phase-03 architecture:
**Autopilot is a thin policy + hook layer over the cortex.session primitive.**

Public API:
    :class:`AutopilotMode`        — observe / assist / autopilot
    :class:`AutopilotPolicy`      — frozen dataclass: mode + thresholds + flags
    :class:`EnforcementSeverity`  — proceed / warn / block
    :class:`EnforcementResult`    — frozen dataclass: severity + reason
    :class:`PolicyEnforcer`       — applies the policy at lifecycle hooks

The enforcer's hooks return a list of :class:`EnforcementResult` so the caller
(typically :class:`cortex.autopilot.service.AutopilotService`) decides how to
surface warnings or stop the operation on a block.

Design note:
    All time comparisons use timezone-aware UTC. The enforcer is stateless
    beyond its immutable policy, and pure functions of the inputs.

## Relaciones

### Recibe de

- `cortex.autopilot.config` (AutopilotConfig)
- `cortex.session.models` (Checkpoint, SessionRecord)
- Dependencias externas/stdlib: `re`, `__future__`, `dataclasses`, `datetime`, `enum`

### Envía a

- `cortex.autopilot`
- `cortex.autopilot.cli`
- `cortex.autopilot.lifecycle`
- `cortex.autopilot.mcp_tools`
- `cortex.autopilot.service`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 374.
Docstrings de símbolos públicos:
- `EnforcementResult.allowed`: True unless severity is BLOCK.
- `AutopilotPolicy.from_config`: Build a policy from an :class:`AutopilotConfig` (YAML-backed).
- `PolicyEnforcer.on_session_open`: Pre-check after the session is opened.
- `PolicyEnforcer.on_checkpoint`: Evaluate after a checkpoint is appended.
- `PolicyEnforcer.on_pre_close`: Evaluate before transitioning the session to a terminal status.

---
Fuente: código de `cortex/autopilot/policies.py` (AST + grafo de imports internos). No se usó documentación previa.
