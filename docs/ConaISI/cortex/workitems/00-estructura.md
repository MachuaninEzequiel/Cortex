# Estructura — `cortex/workitems`

## Para qué existe esta carpeta

cortex.workitems ---------------- Optional work item integration layer for Cortex.

## Árbol interno (código, sin `__pycache__`)

```
workitems/
├── providers/
│   ├── __init__.py
│   ├── base.py
│   └── jira.py
├── __init__.py
├── models.py
└── service.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/workitems/__init__.py` | 16 | cortex.workitems ---------------- Optional work item integration layer for Cortex. |
| `cortex/workitems/models.py` | 46 | cortex.workitems.models ----------------------- Shared models for optional tracked work items imported from external systems. |
| `cortex/workitems/providers/__init__.py` | 7 | Provider implementations for optional external work item sources. |
| `cortex/workitems/providers/base.py` | 28 | cortex.workitems.providers.base ------------------------------- Provider contracts for optional external work item integrations. |
| `cortex/workitems/providers/jira.py` | 167 | cortex.workitems.providers.jira ------------------------------- Read-only Jira provider for importing external work items into Cortex. |
| `cortex/workitems/service.py` | 159 | cortex.workitems.service ------------------------ Service layer for importing and persisting tracked work items. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.documentation`
- `cortex.documentation.data`
- `cortex.documentation.writers`
- `cortex.models`
- `cortex.security.paths`
- `cortex.workitems.models`
- `cortex.workitems.providers.base`
- `cortex.workitems.service`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.core`
- `cortex.workitems`
- `cortex.workitems.providers.base`
- `cortex.workitems.providers.jira`
- `cortex.workitems.service`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
