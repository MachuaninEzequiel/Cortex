# cortex/services/note_service.py

## Qué tiene adentro

- **Ruta de código:** `cortex/services/note_service.py` (245 líneas).
- **Módulo Python:** `cortex.services.note_service`.
- **Docstring del módulo:** cortex.services.note_service ---------------------------- Domain service for creating and persisting *session notes*.
- **Clases definidas:**
  - `_PathOnlyVault`
    - Minimal VaultLike that wraps a bare path for canonical writers.
    - Métodos públicos/especiales: `__init__`, `path`, `index_file`
  - `NoteService`
    - Creates and persists session notes documenting completed work.
    - Métodos públicos/especiales: `__init__`, `create`
    - Métodos internos: `_store_episodic`
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.services.note_service
----------------------------
Domain service for creating and persisting *session notes*.

A "session note" is the Markdown artefact written to the vault when a
working session is closed (``vault/sessions/<id>.md``). It documents what
was done, which files were touched, decisions taken and next steps.

This module was previously named ``cortex.services.session_service`` and
exposed a class called ``SessionService``. As of the Pluggable Middle
architecture (see ``docs/pluggable-middle/``) the *Session primitive* —
a different concept tracking the open-to-close lifecycle of development
work — owns the name ``SessionService`` in ``cortex.session.service``.
To remove the naming clash, this service was renamed ``NoteService`` and
the old import path is kept as a deprecated alias.

Depends on:
- ``cortex.documentation.write_session_note_canonical`` (persistence)
- ``cortex.semantic.vault_reader.VaultReader``           (semantic indexing)
- ``cortex.episodic.memory_store.EpisodicMemoryStore``    (episodic memory)

## Relaciones

### Recibe de

- `cortex.documentation` (write_session_note_canonical)
- `cortex.documentation.data` (SessionData)
- `cortex.documentation.writers` (VaultLike)
- `cortex.models` (MemoryEntry)
- Dependencias externas/stdlib: `logging`, `uuid`, `__future__`, `pathlib`, `typing`

### Envía a

- `cortex.core`
- `cortex.documenter.persistence`
- `cortex.services`
- `cortex.services.session_service`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 245.
Docstrings de símbolos públicos:
- `NoteService.create`: Create a session note and persist it to the vault.

---
Fuente: código de `cortex/services/note_service.py` (AST + grafo de imports internos). No se usó documentación previa.
