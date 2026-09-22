# Estructura — `cortex/pipeline/stages`

## Para qué existe esta carpeta

cortex.pipeline.stages ----------------------- Concrete implementations of PipelineStage for each DevSecDocOps gate.

## Árbol interno (código, sin `__pycache__`)

```
stages/
├── __init__.py
├── documentation.py
├── lint.py
├── security.py
└── test.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/pipeline/stages/__init__.py` | 28 | cortex.pipeline.stages ----------------------- Concrete implementations of PipelineStage for each DevSecDocOps gate. |
| `cortex/pipeline/stages/documentation.py` | 189 | cortex.pipeline.stages.documentation -------------------------------------- DocumentationStage — doc verification and fallback generation gate. |
| `cortex/pipeline/stages/lint.py` | 167 | cortex.pipeline.stages.lint ----------------------------- LintStage — static analysis and code style gate. |
| `cortex/pipeline/stages/security.py` | 173 | cortex.pipeline.stages.security --------------------------------- SecurityStage — dependency vulnerability audit gate. |
| `cortex/pipeline/stages/test.py` | 200 | cortex.pipeline.stages.test ----------------------------- TestStage — test suite execution and coverage enforcement gate. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.pipeline.domain.context`
- `cortex.pipeline.domain.types`
- `cortex.pipeline.stages.documentation`
- `cortex.pipeline.stages.lint`
- `cortex.pipeline.stages.security`
- `cortex.pipeline.stages.test`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.pipeline.stages`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
