# cortex/webgraph/cli.py

## Qué tiene adentro

- **Ruta de código:** `cortex/webgraph/cli.py` (172 líneas).
- **Módulo Python:** `cortex.webgraph.cli`.
- **Funciones de módulo:**
  - `_resolve_project_root(project_root)`
  - `_discover_layout(project_root)` — Discover WorkspaceLayout from a project root path.
  - `_require_config(project_root)`
  - `_resolve_workspace(workspace_file, project_root)`
  - `export_snapshot(mode, output, no_cache, project_root, workspace_file)`
  - `serve(host, port, no_open, project_root, workspace_file)`
  - `doctor(project_root)` — Validate WebGraph runtime prerequisites for one project.

## Para qué sirve

Expone las funciones _resolve_project_root, _discover_layout, _require_config, _resolve_workspace, export_snapshot, serve, doctor. No hay docstring de módulo.

## Relaciones

### Recibe de

- `cortex.webgraph.service` (WebGraphService)
- `cortex.workspace.layout` (WorkspaceLayout)
- Dependencias externas/stdlib: `typer`, `__future__`, `pathlib`

### Envía a

- `cortex.cli.main`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 172.
Docstrings de símbolos públicos:
- `doctor`: Validate WebGraph runtime prerequisites for one project.

---
Fuente: código de `cortex/webgraph/cli.py` (AST + grafo de imports internos). No se usó documentación previa.
