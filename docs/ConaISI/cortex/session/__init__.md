# cortex/session/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/session/__init__.py` (53 líneas).
- **Módulo Python:** `cortex.session`.
- **Docstring del módulo:** cortex.session — Session primitive for the Pluggable Middle architecture.
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.session — Session primitive for the Pluggable Middle architecture.

This package implements the core lifecycle primitive that unites
``cortex-sync``, the (pluggable) middle and ``cortex-documenter``. A Session
is opened automatically when a spec is persisted and closed when the user
runs ``cortex finish-session``.

See ``docs/pluggable-middle/ARQUITECTURA-PLUGGABLE-MIDDLE.md`` §5 for the
full design.

## Relaciones

### Recibe de

- `cortex.session.errors` (InvalidStateTransition, SessionAlreadyExists, SessionError, SessionNotFound, SessionStorageCorrupted)
- `cortex.session.models` (GITLESS_COMMIT_PLACEHOLDER, MAX_VERIFICATION_OUTPUT_BYTES, Checkpoint, CheckpointSource, SessionMode, SessionRecord, SessionStatus, Task, TaskStatus, VerificationHook, VerificationHookResult)
- Dependencias externas/stdlib: `__future__`

### Envía a

- `cortex.ci.diff_io`
- `cortex.cli.session`
- `cortex.cli.session_tui`
- `cortex.core`
- `cortex.documenter.reconstruction`
- `cortex.session.service`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 53.
Reexportes observados:
- cortex.session.errors: InvalidStateTransition, SessionAlreadyExists, SessionError, SessionNotFound, SessionStorageCorrupted
- cortex.session.models: GITLESS_COMMIT_PLACEHOLDER, MAX_VERIFICATION_OUTPUT_BYTES, Checkpoint, CheckpointSource, SessionMode, SessionRecord, SessionStatus, Task, TaskStatus, VerificationHook, VerificationHookResult

---
Fuente: código de `cortex/session/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
