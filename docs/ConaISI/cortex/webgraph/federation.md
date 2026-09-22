# cortex/webgraph/federation.py

## Qué tiene adentro

- **Ruta de código:** `cortex/webgraph/federation.py` (271 líneas).
- **Módulo Python:** `cortex.webgraph.federation`.
- **Clases definidas:**
  - `WorkspaceProject`
  - `FederatedWebGraphService`
    - Compose a unified snapshot from multiple project roots.
    - Métodos públicos/especiales: `__init__`, `build_snapshot`, `export_snapshot`, `get_node_detail`, `get_subgraph`, `resolve_node_path`
    - Métodos internos: `_prefixed`, `_split_prefixed`
- **Funciones de módulo:**
  - `default_workspace_file(project_root)` — Return the default path for the workspace.yaml file.
  - `resolve_workspace_file(workspace_file, project_root)`
  - `write_workspace_file(workspace_file, projects)`
  - `load_workspace_projects(workspace_file)`
  - `_resolve_optional_project_path(project_root, value)`

## Para qué sirve

Define WorkspaceProject, FederatedWebGraphService. No hay docstring de módulo; el propósito se infiere de las clases y métodos listados.

## Relaciones

### Recibe de

- `cortex.webgraph.contracts` (WebGraphEdge, WebGraphMode, WebGraphNode, WebGraphNodeDetail, WebGraphSnapshot, WebGraphStats)
- `cortex.webgraph.service` (WebGraphService)
- `cortex.workspace.layout` (WorkspaceLayout)
- Dependencias externas/stdlib: `hashlib`, `yaml`, `__future__`, `dataclasses`, `pathlib`

### Envía a

- `cortex.webgraph.server`
- `cortex.webgraph.setup`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 271.
Docstrings de símbolos públicos:
- `default_workspace_file`: Return the default path for the workspace.yaml file.

---
Fuente: código de `cortex/webgraph/federation.py` (AST + grafo de imports internos). No se usó documentación previa.
