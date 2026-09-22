# cortex/ci/diff_io.py

## Qué tiene adentro

- **Ruta de código:** `cortex/ci/diff_io.py` (84 líneas).
- **Módulo Python:** `cortex.ci.diff_io`.
- **Docstring del módulo:** cortex.ci.diff_io — Resolve the diff text from CLI inputs.
- **Clases definidas:**
  - `DiffResolutionError` (Exception)
    - Raised when the caller asked for a diff that cannot be produced.
- **Funciones de módulo:**
  - `read_diff_from_args()` — Return the diff text, falling through the three input modes.
  - `_detect_trunk(repo_root)` — Return ``main`` or ``master`` (whichever exists), or ``None``.
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.ci.diff_io — Resolve the diff text from CLI inputs.

Three input modes, in priority order:

1. ``--diff <file>``: read raw text from the file.
2. ``--base-commit`` + ``--head-commit``: run ``git diff base..head``.
3. Auto: ``git diff <trunk>..HEAD`` where trunk is ``main`` or
   ``master`` (whichever exists).

## Relaciones

### Recibe de

- `cortex.session` (git)
- Dependencias externas/stdlib: `__future__`, `pathlib`

### Envía a

- `cortex.cli.ci`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 84.
Docstrings de símbolos públicos:
- `read_diff_from_args`: Return the diff text, falling through the three input modes.

---
Fuente: código de `cortex/ci/diff_io.py` (AST + grafo de imports internos). No se usó documentación previa.
