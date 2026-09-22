# cortex/webgraph/setup.py

## Qué tiene adentro

- **Ruta de código:** `cortex/webgraph/setup.py` (74 líneas).
- **Módulo Python:** `cortex.webgraph.setup`.
- **Funciones de módulo:**
  - `get_missing_webgraph_dependencies()` — Return optional runtime dependencies that are not currently installed.
  - `install_missing_webgraph_dependencies()` — Ensure optional runtime dependencies are available.
  - `install_webgraph(project_root, interactive)`
  - `attach_project_root(workspace_root, project_root)`

## Para qué sirve

Expone las funciones get_missing_webgraph_dependencies, install_missing_webgraph_dependencies, install_webgraph, attach_project_root. No hay docstring de módulo.

## Relaciones

### Recibe de

- `cortex.runtime_context` (slugify)
- `cortex.webgraph.config` (WebGraphConfig)
- `cortex.webgraph.federation` (WorkspaceProject, default_workspace_file, write_workspace_file)
- `cortex.workspace.layout` (WorkspaceLayout)
- Dependencias externas/stdlib: `importlib.util`, `subprocess`, `sys`, `__future__`, `pathlib`

### Envía a

- `cortex.doctor`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 74.
Docstrings de símbolos públicos:
- `get_missing_webgraph_dependencies`: Return optional runtime dependencies that are not currently installed.
- `install_missing_webgraph_dependencies`: Ensure optional runtime dependencies are available.

---
Fuente: código de `cortex/webgraph/setup.py` (AST + grafo de imports internos). No se usó documentación previa.
