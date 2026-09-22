# cortex/webgraph/semantic_source.py

## Qué tiene adentro

- **Ruta de código:** `cortex/webgraph/semantic_source.py` (132 líneas).
- **Módulo Python:** `cortex.webgraph.semantic_source`.
- **Clases definidas:**
  - `SemanticSource`
    - Adapter that projects VaultReader documents into webgraph records.
    - Métodos públicos/especiales: `__init__`, `load_records`
- **Funciones de módulo:**
  - `_read_project_config(project_root)`
  - `_normalize_summary(text, max_chars)`
  - `_semantic_node_type(rel_path, tags)`
  - `_doc_type_from_rel_path(rel_path)` — Best-effort DocType slug from the relative path inside the vault.

## Para qué sirve

Define SemanticSource. No hay docstring de módulo; el propósito se infiere de las clases y métodos listados.

## Relaciones

### Recibe de

- `cortex.episodic.embedder` (Embedder)
- `cortex.semantic.vault_reader` (VaultReader)
- `cortex.webgraph.contracts` (SemanticRecord)
- `cortex.workspace.layout` (WorkspaceLayout)
- Dependencias externas/stdlib: `yaml`, `__future__`, `pathlib`, `typing`

### Envía a

- `cortex.webgraph.service`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 132.

---
Fuente: código de `cortex/webgraph/semantic_source.py` (AST + grafo de imports internos). No se usó documentación previa.
