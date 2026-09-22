# cortex/services/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/services/__init__.py` (41 líneas).
- **Módulo Python:** `cortex.services`.
- **Docstring del módulo:** cortex.services --------------- Domain service layer for Cortex.
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.services
---------------
Domain service layer for Cortex.

This package contains the business-logic services extracted from
the AgentMemory orchestrator. Each service has a single, clear
responsibility (SRP).

Services
--------
- ``SpecService`` → Create and persist implementation specifications.
- ``NoteService`` → Create and persist session notes (vault Markdown).
- ``PRService``   → Store PR context and generate fallback documentation.

The legacy name ``SessionService`` is kept as a deprecated alias of
``NoteService``; new code should not use it. The Session *primitive*
(open / checkpoint / close lifecycle) lives in :mod:`cortex.session`.

Usage
-----
    from cortex.services import SpecService, NoteService, PRService

## Relaciones

### Recibe de

- `cortex.services.note_service` (NoteService)
- `cortex.services.pr_service` (PRService)
- `cortex.services.spec_service` (SpecCreationResult, SpecService)

### Envía a

- `cortex.__init__`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 41.
Reexportes observados:
- cortex.services.note_service: NoteService
- cortex.services.pr_service: PRService
- cortex.services.spec_service: SpecCreationResult, SpecService

---
Fuente: código de `cortex/services/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
