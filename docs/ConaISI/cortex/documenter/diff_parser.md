# cortex/documenter/diff_parser.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documenter/diff_parser.py` (77 líneas).
- **Módulo Python:** `cortex.documenter.diff_parser`.
- **Docstring del módulo:** cortex.documenter.diff_parser — Parse ``git diff --name-status`` output.
- **Clases definidas:**
  - `DiffEntry`
    - One file change between two commits.
- **Funciones de módulo:**
  - `parse_name_status(output)` — Parse the stdout of ``git diff --name-status``.
- **Constantes / símbolos de módulo:** `_STATUS_MAP`, `__all__`

## Para qué sirve

cortex.documenter.diff_parser — Parse ``git diff --name-status`` output.

Used by the reconstruction algorithm to classify changes between a
session's start commit and HEAD. The parser is intentionally lenient:
unknown status letters fall back to ``"modified"`` rather than raising,
so future git versions don't break the documenter.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `__future__`, `dataclasses`, `pathlib`, `typing`

### Envía a

- `cortex.documenter`
- `cortex.documenter.reconstruction`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 77.
Docstrings de símbolos públicos:
- `parse_name_status`: Parse the stdout of ``git diff --name-status``.

---
Fuente: código de `cortex/documenter/diff_parser.py` (AST + grafo de imports internos). No se usó documentación previa.
