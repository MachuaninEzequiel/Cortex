# cortex/webgraph/service.py

## Qué tiene adentro

- **Ruta de código:** `cortex/webgraph/service.py` (289 líneas).
- **Módulo Python:** `cortex.webgraph.service`.
- **Clases definidas:**
  - `WebGraphService`
    - High-level orchestration for building and querying Cortex webgraph snapshots.
    - Métodos públicos/especiales: `__init__`, `build_snapshot`, `export_snapshot`, `get_node_detail`, `resolve_node_path`, `get_subgraph`
- **Funciones de módulo:**
  - `_append_enterprise_nodes(snapshot, project_root)`
  - `_filter_snapshot_by_scope(snapshot, scope)`

## Para qué sirve

Define WebGraphService. No hay docstring de módulo; el propósito se infiere de las clases y métodos listados.

## Relaciones

### Recibe de

- `cortex.enterprise.config` (discover_enterprise_config_path, load_enterprise_config)
- `cortex.runtime_context` (slugify)
- `cortex.webgraph.cache` (WebGraphCache)
- `cortex.webgraph.config` (WebGraphConfig)
- `cortex.webgraph.contracts` (WebGraphEdge, WebGraphMode, WebGraphNode, WebGraphNodeDetail, WebGraphSnapshot)
- `cortex.webgraph.episodic_source` (EpisodicSource)
- `cortex.webgraph.graph_builder` (GraphBuilder)
- `cortex.webgraph.semantic_source` (SemanticSource)
- `cortex.workspace.layout` (WorkspaceLayout)
- Dependencias externas/stdlib: `__future__`, `collections`, `pathlib`

### Envía a

- `cortex.webgraph`
- `cortex.webgraph.cli`
- `cortex.webgraph.federation`
- `cortex.webgraph.server`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 289.

---
Fuente: código de `cortex/webgraph/service.py` (AST + grafo de imports internos). No se usó documentación previa.
