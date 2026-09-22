# cortex/ci/session_matcher.py

## Qué tiene adentro

- **Ruta de código:** `cortex/ci/session_matcher.py` (49 líneas).
- **Módulo Python:** `cortex.ci.session_matcher`.
- **Docstring del módulo:** cortex.ci.session_matcher — find the Session matching a PR.
- **Funciones de módulo:**
  - `find_session_for_pr(storage)` — Resolve the Session that owns the given PR.
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.ci.session_matcher — find the Session matching a PR.

Priority is intentional: explicit > base_commit > head_branch > none.
The caller decides what to do with a ``"none"`` match (typically: emit a
warning and exit with code 2 — see ``cortex.ci.validator``).

## Relaciones

### Recibe de

- `cortex.ci.result` (SessionMatchKind)
- `cortex.session.models` (SessionRecord)
- `cortex.session.storage` (SessionStorage)
- Dependencias externas/stdlib: `__future__`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 49.
Docstrings de símbolos públicos:
- `find_session_for_pr`: Resolve the Session that owns the given PR.

---
Fuente: código de `cortex/ci/session_matcher.py` (AST + grafo de imports internos). No se usó documentación previa.
