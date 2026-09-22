# cortex/workitems/providers/base.py

## Qué tiene adentro

- **Ruta de código:** `cortex/workitems/providers/base.py` (28 líneas).
- **Módulo Python:** `cortex.workitems.providers.base`.
- **Docstring del módulo:** cortex.workitems.providers.base ------------------------------- Provider contracts for optional external work item integrations.
- **Clases definidas:**
  - `WorkItemProvider` (ABC)
    - Abstract read-only provider for external work items.
    - Métodos públicos/especiales: `source_name`, `is_configured`, `get_item`

## Para qué sirve

cortex.workitems.providers.base
-------------------------------
Provider contracts for optional external work item integrations.

## Relaciones

### Recibe de

- `cortex.workitems.models` (TrackedItem)
- Dependencias externas/stdlib: `__future__`, `abc`

### Envía a

- `cortex.workitems.providers`
- `cortex.workitems.providers.jira`
- `cortex.workitems.service`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 28.
Docstrings de símbolos públicos:
- `WorkItemProvider.source_name`: Human-readable provider identifier.
- `WorkItemProvider.is_configured`: Whether the provider has enough configuration to operate.
- `WorkItemProvider.get_item`: Fetch and normalize one external work item.

---
Fuente: código de `cortex/workitems/providers/base.py` (AST + grafo de imports internos). No se usó documentación previa.
