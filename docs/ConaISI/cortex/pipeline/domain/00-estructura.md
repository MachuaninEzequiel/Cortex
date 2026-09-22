# Estructura — `cortex/pipeline/domain`

## Para qué existe esta carpeta

cortex.pipeline.domain ----------------------- Pure domain types for the pipeline module.

## Árbol interno (código, sin `__pycache__`)

```
domain/
├── __init__.py
├── context.py
├── protocols.py
└── types.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/pipeline/domain/__init__.py` | 10 | cortex.pipeline.domain ----------------------- Pure domain types for the pipeline module. |
| `cortex/pipeline/domain/context.py` | 168 | cortex.pipeline.domain.context -------------------------------- PipelineContext — the shared execution context passed to every stage. |
| `cortex/pipeline/domain/protocols.py` | 78 | cortex.pipeline.domain.protocols ---------------------------------- The PipelineStage Protocol — the contract that every stage must satisfy. |
| `cortex/pipeline/domain/types.py` | 184 | cortex.pipeline.domain.types ----------------------------- Core value types for the DevSecDocOps pipeline. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.pipeline.domain.types`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.pipeline`
- `cortex.pipeline.domain.protocols`
- `cortex.pipeline.orchestrator`
- `cortex.pipeline.runners.github`
- `cortex.pipeline.stages.documentation`
- `cortex.pipeline.stages.lint`
- `cortex.pipeline.stages.security`
- `cortex.pipeline.stages.test`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
