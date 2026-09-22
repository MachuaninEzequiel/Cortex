# cortex/documenter/adr_evaluator.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documenter/adr_evaluator.py` (115 líneas).
- **Módulo Python:** `cortex.documenter.adr_evaluator`.
- **Docstring del módulo:** cortex.documenter.adr_evaluator — Surface ADR candidates from checkpoints.
- **Clases definidas:**
  - `ADRSuggestion`
    - One candidate ADR surfaced from session evidence.
- **Funciones de módulo:**
  - `suggest_adrs(checkpoints, diff_text)` — Return a list of ADR candidates derived from *checkpoints*.
  - `_title_from_note(note)` — Build a short ADR title from a checkpoint note.
- **Constantes / símbolos de módulo:** `_DECISION_PATTERNS`, `__all__`

## Para qué sirve

cortex.documenter.adr_evaluator — Surface ADR candidates from checkpoints.

The architecture (§12 of the documenter subagent) requires three criteria
to merit an ADR: hard to reverse, surprising without context, and a real
trade-off. Pure-Python evaluation cannot judge those qualities; what we
*can* do is detect keyword signals in checkpoint notes and flag them as
*candidates*, with the rationale visible to the LLM or human reviewer
in interactive mode (Phase 04).

When no checkpoints exist (BYO mode), no ADR candidates are surfaced —
there is no narrated decision to mine.

## Relaciones

### Recibe de

- `cortex.session.models` (Checkpoint)
- Dependencias externas/stdlib: `re`, `__future__`, `collections.abc`, `dataclasses`

### Envía a

- `cortex.documenter`
- `cortex.documenter.persistence`
- `cortex.documenter.reconstruction`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 115.
Docstrings de símbolos públicos:
- `suggest_adrs`: Return a list of ADR candidates derived from *checkpoints*.

---
Fuente: código de `cortex/documenter/adr_evaluator.py` (AST + grafo de imports internos). No se usó documentación previa.
