# cortex/session/errors.py

## Qué tiene adentro

- **Ruta de código:** `cortex/session/errors.py` (49 líneas).
- **Módulo Python:** `cortex.session.errors`.
- **Docstring del módulo:** cortex.session.errors — Domain exceptions for the Session primitive.
- **Clases definidas:**
  - `SessionError` (Exception)
    - Base class for all errors raised by :mod:`cortex.session`.
  - `SessionNotFound` (SessionError)
    - Raised when a ``session_id`` does not exist in storage.
  - `SessionAlreadyExists` (SessionError)
    - Raised when trying to open a Session whose id already exists.
  - `InvalidStateTransition` (SessionError)
    - Raised when an operation is incompatible with the current status.
  - `SessionStorageCorrupted` (SessionError)
    - Raised when a session YAML on disk cannot be parsed.

## Para qué sirve

cortex.session.errors — Domain exceptions for the Session primitive.

All exceptions inherit from :class:`SessionError`. Callers should catch the
base class when they want to translate any session failure into a generic
error response (e.g. MCP tool responses, CLI exit messages).

The hierarchy is intentionally flat — there is no need for sub-trees while
the surface area is small. New exceptions added later should also inherit
directly from :class:`SessionError` unless a real grouping exists.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `__future__`

### Envía a

- `cortex.autopilot.cli`
- `cortex.autopilot.errors`
- `cortex.autopilot.mcp_tools`
- `cortex.autopilot.service`
- `cortex.cli.session`
- `cortex.session`
- `cortex.session.service`
- `cortex.session.storage`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 49.

---
Fuente: código de `cortex/session/errors.py` (AST + grafo de imports internos). No se usó documentación previa.
