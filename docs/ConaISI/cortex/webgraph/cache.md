# cortex/webgraph/cache.py

## Qué tiene adentro

- **Ruta de código:** `cortex/webgraph/cache.py` (84 líneas).
- **Módulo Python:** `cortex.webgraph.cache`.
- **Clases definidas:**
  - `WebGraphCache`
    - Persistent snapshot cache for the hybrid webgraph.
    - Métodos públicos/especiales: `__init__`, `snapshot_path`, `meta_path`, `load_snapshot`, `store_snapshot`, `compute_fingerprint`
    - Métodos internos: `_meta_key`, `_hash_tree`

## Para qué sirve

Define WebGraphCache. No hay docstring de módulo; el propósito se infiere de las clases y métodos listados.

## Relaciones

### Recibe de

- `cortex.webgraph.contracts` (WebGraphSnapshot)
- `cortex.workspace.layout` (WorkspaceLayout)
- Dependencias externas/stdlib: `hashlib`, `json`, `__future__`, `pathlib`, `typing`

### Envía a

- `cortex.webgraph.service`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 84.

---
Fuente: código de `cortex/webgraph/cache.py` (AST + grafo de imports internos). No se usó documentación previa.
