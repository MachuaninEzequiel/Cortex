# cortex/webgraph/server.py

## Qué tiene adentro

- **Ruta de código:** `cortex/webgraph/server.py` (144 líneas).
- **Módulo Python:** `cortex.webgraph.server`.
- **Funciones de módulo:**
  - `create_app(project_root)`
  - `run_server(project_root)`

## Para qué sirve

Expone las funciones create_app, run_server. No hay docstring de módulo.

## Relaciones

### Recibe de

- `cortex.webgraph.config` (WebGraphConfig)
- `cortex.webgraph.contracts` (WebGraphMode)
- `cortex.webgraph.style` (build_legend)
- `cortex.webgraph.federation` (FederatedWebGraphService)
- `cortex.webgraph.openers` (open_path, resolve_safe_vault_path)
- `cortex.webgraph.service` (WebGraphService)
- `cortex.workspace.layout` (WorkspaceLayout)
- Dependencias externas/stdlib: `__future__`, `pathlib`, `typing`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 144.

---
Fuente: código de `cortex/webgraph/server.py` (AST + grafo de imports internos). No se usó documentación previa.
