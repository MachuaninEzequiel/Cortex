# Estructura — `cortex/webgraph`

## Para qué existe esta carpeta

cortex.webgraph ---------------- Hybrid memory graph projection for Cortex.

## Árbol interno (código, sin `__pycache__`)

```
webgraph/
├── static/
│   ├── app.js
│   └── style.css
├── templates/
│   └── index.html
├── __init__.py
├── cache.py
├── cli.py
├── config.py
├── contracts.py
├── episodic_source.py
├── federation.py
├── graph_builder.py
├── openers.py
├── relation_builder.py
├── semantic_source.py
├── server.py
├── service.py
├── setup.py
└── style.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/webgraph/__init__.py` | 11 | cortex.webgraph ---------------- Hybrid memory graph projection for Cortex. |
| `cortex/webgraph/cache.py` | 84 | WebGraphCache |
| `cortex/webgraph/cli.py` | 172 | _resolve_project_root, _discover_layout, _require_config, _resolve_workspace, export_snapshot, serve, doctor |
| `cortex/webgraph/config.py` | 53 | WebGraphConfig |
| `cortex/webgraph/contracts.py` | 95 | WebGraphCapabilities, WebGraphStats, WebGraphNode, WebGraphEdge, WebGraphSnapshot, WebGraphNodeDetail, SemanticRecord, EpisodicRecord |
| `cortex/webgraph/episodic_source.py` | 95 | EpisodicSource, _read_project_config, _episodic_node_type, _normalize_summary |
| `cortex/webgraph/federation.py` | 271 | WorkspaceProject, FederatedWebGraphService, default_workspace_file, resolve_workspace_file, write_workspace_file, load_workspace_projects, _resolve_optional_project_path |
| `cortex/webgraph/graph_builder.py` | 109 | GraphBuilder |
| `cortex/webgraph/openers.py` | 28 | resolve_safe_vault_path, open_path |
| `cortex/webgraph/relation_builder.py` | 489 | RelationBuilder, _slug, _tokenize, _identifier_tokens, _cosine_similarity |
| `cortex/webgraph/semantic_source.py` | 132 | SemanticSource, _read_project_config, _normalize_summary, _semantic_node_type, _doc_type_from_rel_path |
| `cortex/webgraph/server.py` | 144 | create_app, run_server |
| `cortex/webgraph/service.py` | 289 | WebGraphService, _append_enterprise_nodes, _filter_snapshot_by_scope |
| `cortex/webgraph/setup.py` | 74 | get_missing_webgraph_dependencies, install_missing_webgraph_dependencies, install_webgraph, attach_project_root |
| `cortex/webgraph/style.py` | 171 | cortex.webgraph.style - Node and edge styling for the canonical webgraph. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.documentation.doc_type`
- `cortex.enterprise.config`
- `cortex.episodic.embedder`
- `cortex.episodic.memory_store`
- `cortex.runtime_context`
- `cortex.semantic.vault_reader`
- `cortex.webgraph.cache`
- `cortex.webgraph.config`
- `cortex.webgraph.contracts`
- `cortex.webgraph.episodic_source`
- `cortex.webgraph.federation`
- `cortex.webgraph.graph_builder`
- `cortex.webgraph.openers`
- `cortex.webgraph.relation_builder`
- `cortex.webgraph.semantic_source`
- `cortex.webgraph.service`
- `cortex.webgraph.style`
- `cortex.workspace.layout`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.cli.main`
- `cortex.doctor`
- `cortex.webgraph`
- `cortex.webgraph.cache`
- `cortex.webgraph.cli`
- `cortex.webgraph.config`
- `cortex.webgraph.episodic_source`
- `cortex.webgraph.federation`
- `cortex.webgraph.graph_builder`
- `cortex.webgraph.relation_builder`
- `cortex.webgraph.semantic_source`
- `cortex.webgraph.server`
- `cortex.webgraph.service`
- `cortex.webgraph.setup`

Assets de UI documentados aparte (no son `.py`):

- `templates/index.html` → `templates_index.md`
- `static/app.js` → `static_app.md`
- `static/style.css` → `static_style.md`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
