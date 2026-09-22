# Estructura — `cortex/pipeline/runners`

## Para qué existe esta carpeta

cortex.pipeline.runners ------------------------ CI/CD provider adapters for the Cortex pipeline.

## Árbol interno (código, sin `__pycache__`)

```
runners/
├── __init__.py
└── github.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/pipeline/runners/__init__.py` | 17 | cortex.pipeline.runners ------------------------ CI/CD provider adapters for the Cortex pipeline. |
| `cortex/pipeline/runners/github.py` | 333 | cortex.pipeline.runners.github -------------------------------- GitHubActionsRunner — generates GitHub Actions workflow YAML from a pipeline stage configuration. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.pipeline.domain.types`
- `cortex.pipeline.runners.github`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.pipeline.runners`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
