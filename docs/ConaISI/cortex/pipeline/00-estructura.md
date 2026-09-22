# Estructura — `cortex/pipeline`

## Para qué existe esta carpeta

cortex.pipeline --------------- DevSecDocOps Pipeline — formal Python abstraction for CI/CD stages.

## Árbol interno (código, sin `__pycache__`)

```
pipeline/
├── domain/
│   ├── __init__.py
│   ├── context.py
│   ├── protocols.py
│   └── types.py
├── runners/
│   ├── __init__.py
│   └── github.py
├── stages/
│   ├── __init__.py
│   ├── documentation.py
│   ├── lint.py
│   ├── security.py
│   └── test.py
├── __init__.py
└── orchestrator.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/pipeline/__init__.py` | 57 | cortex.pipeline --------------- DevSecDocOps Pipeline — formal Python abstraction for CI/CD stages. |
| `cortex/pipeline/domain/__init__.py` | 10 | cortex.pipeline.domain ----------------------- Pure domain types for the pipeline module. |
| `cortex/pipeline/domain/context.py` | 168 | cortex.pipeline.domain.context -------------------------------- PipelineContext — the shared execution context passed to every stage. |
| `cortex/pipeline/domain/protocols.py` | 78 | cortex.pipeline.domain.protocols ---------------------------------- The PipelineStage Protocol — the contract that every stage must satisfy. |
| `cortex/pipeline/domain/types.py` | 184 | cortex.pipeline.domain.types ----------------------------- Core value types for the DevSecDocOps pipeline. |
| `cortex/pipeline/orchestrator.py` | 117 | cortex.pipeline.orchestrator ----------------------------- PipelineOrchestrator — executes stages in order, enforces gates. |
| `cortex/pipeline/runners/__init__.py` | 17 | cortex.pipeline.runners ------------------------ CI/CD provider adapters for the Cortex pipeline. |
| `cortex/pipeline/runners/github.py` | 333 | cortex.pipeline.runners.github -------------------------------- GitHubActionsRunner — generates GitHub Actions workflow YAML from a pipeline stage configuration. |
| `cortex/pipeline/stages/__init__.py` | 28 | cortex.pipeline.stages ----------------------- Concrete implementations of PipelineStage for each DevSecDocOps gate. |
| `cortex/pipeline/stages/documentation.py` | 189 | cortex.pipeline.stages.documentation -------------------------------------- DocumentationStage — doc verification and fallback generation gate. |
| `cortex/pipeline/stages/lint.py` | 167 | cortex.pipeline.stages.lint ----------------------------- LintStage — static analysis and code style gate. |
| `cortex/pipeline/stages/security.py` | 173 | cortex.pipeline.stages.security --------------------------------- SecurityStage — dependency vulnerability audit gate. |
| `cortex/pipeline/stages/test.py` | 200 | cortex.pipeline.stages.test ----------------------------- TestStage — test suite execution and coverage enforcement gate. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.pipeline.domain.context`
- `cortex.pipeline.domain.protocols`
- `cortex.pipeline.domain.types`
- `cortex.pipeline.orchestrator`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.__init__`
- `cortex.pipeline`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
