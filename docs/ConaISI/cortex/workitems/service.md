# cortex/workitems/service.py

## Qué tiene adentro

- **Ruta de código:** `cortex/workitems/service.py` (159 líneas).
- **Módulo Python:** `cortex.workitems.service`.
- **Docstring del módulo:** cortex.workitems.service ------------------------ Service layer for importing and persisting tracked work items.
- **Clases definidas:**
  - `_PathOnlyVault`
    - Minimal VaultLike that wraps a bare path for canonical writers.
    - Métodos públicos/especiales: `__init__`, `path`, `index_file`
  - `WorkItemService`
    - Imports, persists, and retrieves tracked items from optional providers.
    - Métodos públicos/especiales: `__init__`, `import_item`, `get_item_note`, `list_item_notes`, `has_provider`
    - Métodos internos: `_provider`, `_write_item_note`, `_store_episodic`, `_slug`
- **Constantes / símbolos de módulo:** `_STATUS_MAP`

## Para qué sirve

cortex.workitems.service
------------------------
Service layer for importing and persisting tracked work items.

## Relaciones

### Recibe de

- `cortex.documentation` (write_hu_note)
- `cortex.documentation.data` (HUData)
- `cortex.documentation.writers` (VaultLike)
- `cortex.models` (MemoryEntry)
- `cortex.security.paths` (resolve_safe)
- `cortex.workitems.models` (TrackedItem)
- `cortex.workitems.providers.base` (WorkItemProvider)
- Dependencias externas/stdlib: `re`, `__future__`, `datetime`, `pathlib`, `typing`

### Envía a

- `cortex.core`
- `cortex.workitems`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 159.

---
Fuente: código de `cortex/workitems/service.py` (AST + grafo de imports internos). No se usó documentación previa.
