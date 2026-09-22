# cortex/webgraph/episodic_source.py

## Qué tiene adentro

- **Ruta de código:** `cortex/webgraph/episodic_source.py` (95 líneas).
- **Módulo Python:** `cortex.webgraph.episodic_source`.
- **Clases definidas:**
  - `EpisodicSource`
    - Adapter that projects episodic memory entries into webgraph records.
    - Métodos públicos/especiales: `__init__`, `load_records`
- **Funciones de módulo:**
  - `_read_project_config(project_root)`
  - `_episodic_node_type(memory_type)`
  - `_normalize_summary(text, max_chars)`

## Para qué sirve

Define EpisodicSource. No hay docstring de módulo; el propósito se infiere de las clases y métodos listados.

## Relaciones

### Recibe de

- `cortex.episodic.embedder` (Embedder)
- `cortex.episodic.memory_store` (EpisodicMemoryStore)
- `cortex.runtime_context` (resolve_episodic_persist_dir)
- `cortex.webgraph.contracts` (EpisodicRecord)
- `cortex.workspace.layout` (WorkspaceLayout)
- Dependencias externas/stdlib: `yaml`, `__future__`, `pathlib`, `typing`

### Envía a

- `cortex.webgraph.service`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 95.

---
Fuente: código de `cortex/webgraph/episodic_source.py` (AST + grafo de imports internos). No se usó documentación previa.
