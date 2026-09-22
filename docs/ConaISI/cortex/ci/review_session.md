# cortex/ci/review_session.py

## Qué tiene adentro

- **Ruta de código:** `cortex/ci/review_session.py` (157 líneas).
- **Módulo Python:** `cortex.ci.review_session`.
- **Docstring del módulo:** cortex.ci.review_session — CI-owned review-session helpers (Level 3).
- **Funciones de módulo:**
  - `open_review_session(service)` — Open a fresh review session.
  - `report_ci_checkpoint(service)` — Append a ``CI_BOT`` checkpoint to the review session.
  - `close_review_session(service)` — Close the review session into a terminal status.
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.ci.review_session — CI-owned review-session helpers (Level 3).

A review session uses the existing Session primitive verbatim. The only
new model bits live in ``cortex.session.models``:

* ``CheckpointSource.CI_BOT`` — the source value emitted by these helpers.
* ``SessionMode.CI_REVIEW`` — the mode the close-time inference picks
  when every checkpoint comes from ``CI_BOT``.

## Relaciones

### Recibe de

- `cortex.session.models` (CheckpointSource, SessionRecord, SessionStatus)
- `cortex.session.service` (SessionService)
- Dependencias externas/stdlib: `__future__`, `collections.abc`, `datetime`, `pathlib`, `typing`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 157.
Docstrings de símbolos públicos:
- `open_review_session`: Open a fresh review session.
- `report_ci_checkpoint`: Append a ``CI_BOT`` checkpoint to the review session.
- `close_review_session`: Close the review session into a terminal status.

---
Fuente: código de `cortex/ci/review_session.py` (AST + grafo de imports internos). No se usó documentación previa.
