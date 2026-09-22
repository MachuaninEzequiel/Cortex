# cortex/autopilot/errors.py

## Qué tiene adentro

- **Ruta de código:** `cortex/autopilot/errors.py` (37 líneas).
- **Módulo Python:** `cortex.autopilot.errors`.
- **Docstring del módulo:** cortex.autopilot.errors — Exceptions raised by the Autopilot module.
- **Clases definidas:**
  - `AutopilotError` (Exception)
    - Base exception for all Autopilot errors.
  - `ConfigError` (AutopilotError)
    - Raised when the Autopilot configuration is invalid or missing.
  - `NoActiveSessionError` (AutopilotError)
    - Raised when an operation requires an active session and none exists.
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.autopilot.errors — Exceptions raised by the Autopilot module.

Phase 03 removed ``SessionNotFoundError`` from this module: callers now
import :class:`cortex.session.errors.SessionNotFound` from the canonical
session primitive. The legacy name is re-exported as a deprecated alias
so external code does not break instantly; the alias will be removed in
the next major release.

## Relaciones

### Recibe de

- `cortex.session.errors` (SessionNotFound)
- Dependencias externas/stdlib: `__future__`

### Envía a

- `cortex.autopilot.cli`
- `cortex.autopilot.mcp_tools`
- `cortex.autopilot.service`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 37.

---
Fuente: código de `cortex/autopilot/errors.py` (AST + grafo de imports internos). No se usó documentación previa.
