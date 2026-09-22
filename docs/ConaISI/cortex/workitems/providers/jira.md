# cortex/workitems/providers/jira.py

## Qué tiene adentro

- **Ruta de código:** `cortex/workitems/providers/jira.py` (167 líneas).
- **Módulo Python:** `cortex.workitems.providers.jira`.
- **Docstring del módulo:** cortex.workitems.providers.jira ------------------------------- Read-only Jira provider for importing external work items into Cortex.
- **Clases definidas:**
  - `JiraProvider` (WorkItemProvider)
    - Read-only Jira Cloud/Server REST API provider.
    - Métodos públicos/especiales: `__init__`, `from_config`, `source_name`, `is_configured`, `get_item`
    - Métodos internos: `_request_json`, `_to_tracked_item`, `_extract_description`, `_flatten_adf`, `_extract_acceptance_criteria`, `_map_kind`

## Para qué sirve

cortex.workitems.providers.jira
-------------------------------
Read-only Jira provider for importing external work items into Cortex.

## Relaciones

### Recibe de

- `cortex.workitems.models` (TrackedItem, WorkItemKind, WorkItemSource)
- `cortex.workitems.providers.base` (WorkItemProvider)
- Dependencias externas/stdlib: `base64`, `json`, `os`, `urllib.error`, `urllib.parse`, `urllib.request`, `__future__`, `typing`

### Envía a

- `cortex.core`
- `cortex.workitems.providers`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 167.

---
Fuente: código de `cortex/workitems/providers/jira.py` (AST + grafo de imports internos). No se usó documentación previa.
