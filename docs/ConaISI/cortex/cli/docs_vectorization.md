# cortex/cli/docs_vectorization.py

## Qué tiene adentro

- **Ruta de código:** `cortex/cli/docs_vectorization.py` (122 líneas).
- **Módulo Python:** `cortex.cli.docs_vectorization`.
- **Docstring del módulo:** cortex.cli.docs_vectorization - ``cortex docs vectorization`` subcommands.
- **Funciones de módulo:**
  - `_vec_main()` — Vector cache operations.
  - `_resolve_cache(project_root)`
  - `stats(project_root, json_output)` — Print vector cache statistics.
  - `compact(project_root)` — Reclaim space from invalidated entries (rewrites chunks.bin).
  - `clear(project_root, yes)` — Delete every cached vector. The cache rebuilds on the next sync.

## Para qué sirve

cortex.cli.docs_vectorization - ``cortex docs vectorization`` subcommands.

Inspects, compacts and clears the vector cache introduced in Fase 06 of the
canonical-documentation initiative.

## Relaciones

### Recibe de

- `cortex.semantic.vector_cache` (VectorCache)
- `cortex.workspace.layout` (WorkspaceLayout)
- Dependencias externas/stdlib: `json`, `os`, `typer`, `__future__`, `pathlib`

### Envía a

- `cortex.cli.docs_subcommand`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 122.
Docstrings de símbolos públicos:
- `stats`: Print vector cache statistics.
- `compact`: Reclaim space from invalidated entries (rewrites chunks.bin).
- `clear`: Delete every cached vector. The cache rebuilds on the next sync.

---
Fuente: código de `cortex/cli/docs_vectorization.py` (AST + grafo de imports internos). No se usó documentación previa.
