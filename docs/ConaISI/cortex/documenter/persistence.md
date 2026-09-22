# cortex/documenter/persistence.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documenter/persistence.py` (482 líneas).
- **Módulo Python:** `cortex.documenter.persistence`.
- **Docstring del módulo:** cortex.documenter.persistence — Persist a ReconstructionOutput.
- **Clases definidas:**
  - `FinishOverrides`
    - Hook point for Phase 04's interactive mode.
  - `FinishSessionResult`
    - What ``finalize`` reports back to the caller.
  - `_VaultPathOnly`
    - Minimal :class:`VaultLike` wrapping a bare path for canonical writers.
    - Métodos públicos/especiales: `__init__`, `path`, `index_file`
  - `DocumenterPersister`
    - Side-effecting closer of a reconstructed session.
    - Métodos públicos/especiales: `__init__`, `finalize`
    - Métodos internos: `_write_session_note`, `_self_review_draft`, `_write_adrs`, `_build_summary`
- **Funciones de módulo:**
  - `_summarize_tasks(tasks)` — Bundle task data the way the session template expects it.
  - `_build_draft_body_for_review()` — Compose a single text blob the self-review can scan.
- **Constantes / símbolos de módulo:** `_PLACEHOLDER_TOKENS`, `_SUCCESS_CLAIM_PATTERNS`, `_SELF_REVIEW_TAG`, `__all__`

## Para qué sirve

cortex.documenter.persistence — Persist a ReconstructionOutput.

Given the read-only :class:`ReconstructionOutput` produced by the
:class:`Reconstructor`, the :class:`DocumenterPersister` writes the
artefacts to disk and closes the session:

1. Build a ``SessionData`` and persist it via :class:`NoteService`.
2. For every :class:`ADRSuggestion`, build an ``ADRData`` and persist it
   via :func:`write_adr_note`.
3. Update CONTEXT.md if applicable (deferred — Phase 01 leaves this as
   a no-op and Phase 04 will integrate the glossary loop).
4. Close the underlying :class:`SessionRecord` via :class:`SessionService`
   with the documenter's verdict.

The persister is **idempotent**: calling ``finalize`` on an already-
closed session returns the existing artefact paths without re-writing.

Phase 08 / T8.3 added a *self-review* pass over the about-to-persist
draft. It is **informational only** — never blocks persistence. When
the scan finds placeholders, unreferenced files, or success claims
without evidence, the resulting warnings are appended to the note's
``next_steps`` (prefixed ``[self-review]``) and the ``auto-draft`` tag
is attached so consumers can filter on it. Blocking here would create
infinite loops in the agentic flow; we surface, not gate.

## Relaciones

### Recibe de

- `cortex.documentation.data` (ADRData)
- `cortex.documentation.writers` (write_adr_note)
- `cortex.documenter.adr_evaluator` (ADRSuggestion)
- `cortex.documenter.reconstruction` (ReconstructionOutput)
- `cortex.services.note_service` (NoteService)
- `cortex.session.models` (SessionStatus, Task, TaskStatus)
- `cortex.session.service` (SessionService)
- Dependencias externas/stdlib: `logging`, `__future__`, `collections.abc`, `dataclasses`, `pathlib`

### Envía a

- `cortex.documenter`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 482.
Docstrings de símbolos públicos:
- `DocumenterPersister.finalize`: Persist artefacts and close the session.

---
Fuente: código de `cortex/documenter/persistence.py` (AST + grafo de imports internos). No se usó documentación previa.
