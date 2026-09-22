# cortex/security/paths.py

## Qué tiene adentro

- **Ruta de código:** `cortex/security/paths.py` (64 líneas).
- **Módulo Python:** `cortex.security.paths`.
- **Docstring del módulo:** cortex.security.paths --------------------- Centralised path-safety helpers for Cortex.
- **Clases definidas:**
  - `PathSecurityError` (ValueError)
    - Raised when a path escapes the allowed root directory.
- **Funciones de módulo:**
  - `resolve_safe(root, rel)` — Resolve *rel* under *root* and enforce that the result stays inside *root*.
  - `validate_under_root(path, root)` — Validate that an already-constructed *path* stays inside *root*.

## Para qué sirve

cortex.security.paths
---------------------
Centralised path-safety helpers for Cortex.

Every component that builds filesystem paths from operational input
should use these helpers instead of ad-hoc string concatenation.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `__future__`, `pathlib`

### Envía a

- `cortex.mcp.tools.search`
- `cortex.security`
- `cortex.semantic.vault_reader`
- `cortex.workitems.service`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 64.
Docstrings de símbolos públicos:
- `resolve_safe`: Resolve *rel* under *root* and enforce that the result stays inside *root*.
- `validate_under_root`: Validate that an already-constructed *path* stays inside *root*.

---
Fuente: código de `cortex/security/paths.py` (AST + grafo de imports internos). No se usó documentación previa.
