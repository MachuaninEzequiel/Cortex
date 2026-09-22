# Estructura — `cortex/workitems/providers`

## Para qué existe esta carpeta

Provider implementations for optional external work item sources.

## Árbol interno (código, sin `__pycache__`)

```
providers/
├── __init__.py
├── base.py
└── jira.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/workitems/providers/__init__.py` | 7 | Provider implementations for optional external work item sources. |
| `cortex/workitems/providers/base.py` | 28 | cortex.workitems.providers.base ------------------------------- Provider contracts for optional external work item integrations. |
| `cortex/workitems/providers/jira.py` | 167 | cortex.workitems.providers.jira ------------------------------- Read-only Jira provider for importing external work items into Cortex. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.workitems.models`
- `cortex.workitems.providers.base`
- `cortex.workitems.providers.jira`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.core`
- `cortex.workitems.providers`
- `cortex.workitems.providers.jira`
- `cortex.workitems.service`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
