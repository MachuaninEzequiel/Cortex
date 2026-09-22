# cortex/workitems/models.py

## Qué tiene adentro

- **Ruta de código:** `cortex/workitems/models.py` (46 líneas).
- **Módulo Python:** `cortex.workitems.models`.
- **Docstring del módulo:** cortex.workitems.models ----------------------- Shared models for optional tracked work items imported from external systems.
- **Clases definidas:**
  - `WorkItemSource` (str, Enum)
  - `WorkItemKind` (str, Enum)
  - `TrackedItem` (BaseModel)
    - Canonical internal representation of an imported work item.

## Para qué sirve

cortex.workitems.models
-----------------------
Shared models for optional tracked work items imported from external systems.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `__future__`, `datetime`, `enum`, `typing`, `pydantic`

### Envía a

- `cortex.workitems`
- `cortex.workitems.providers.base`
- `cortex.workitems.providers.jira`
- `cortex.workitems.service`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 46.

---
Fuente: código de `cortex/workitems/models.py` (AST + grafo de imports internos). No se usó documentación previa.
