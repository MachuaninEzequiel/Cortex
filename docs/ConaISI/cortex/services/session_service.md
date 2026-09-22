# cortex/services/session_service.py

## Qué tiene adentro

- **Ruta de código:** `cortex/services/session_service.py` (33 líneas).
- **Módulo Python:** `cortex.services.session_service`.
- **Docstring del módulo:** Deprecated alias for :mod:`cortex.services.note_service`.
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

Deprecated alias for :mod:`cortex.services.note_service`.

This module used to host the ``SessionService`` class that creates and
persists *session notes*. As of the Pluggable Middle architecture, the
class was renamed to ``NoteService`` and moved to
``cortex.services.note_service`` to disambiguate from the new Session
primitive at :mod:`cortex.session.service`.

Importing from this module emits a :class:`DeprecationWarning` and re-
exports ``NoteService`` under the legacy name ``SessionService``. New
code should import from ``cortex.services.note_service`` instead.

## Relaciones

### Recibe de

- `cortex.services.note_service` (NoteService)
- Dependencias externas/stdlib: `warnings`, `__future__`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 33.

---
Fuente: código de `cortex/services/session_service.py` (AST + grafo de imports internos). No se usó documentación previa.
