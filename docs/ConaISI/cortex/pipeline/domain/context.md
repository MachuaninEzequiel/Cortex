# cortex/pipeline/domain/context.py

## Qué tiene adentro

- **Ruta de código:** `cortex/pipeline/domain/context.py` (168 líneas).
- **Módulo Python:** `cortex.pipeline.domain.context`.
- **Docstring del módulo:** cortex.pipeline.domain.context -------------------------------- PipelineContext — the shared execution context passed to every stage.
- **Clases definidas:**
  - `PipelineContext`
    - Shared execution context for all pipeline stages.
    - Métodos públicos/especiales: `from_pr_context`, `from_env`, `get_stage_output`, `set_stage_output`

## Para qué sirve

cortex.pipeline.domain.context
--------------------------------
PipelineContext — the shared execution context passed to every stage.

This is the single source of truth for a pipeline run. Every stage
reads from it (changed files, PR metadata, config) and may write
results back into the shared ``stage_outputs`` dict.

Design decisions:
- Uses a regular dataclass (not frozen) because the orchestrator
  populates ``stage_outputs`` as stages complete.
- Factory methods make construction from different sources explicit.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `__future__`, `dataclasses`, `pathlib`, `typing`

### Envía a

- `cortex.pipeline`
- `cortex.pipeline.orchestrator`
- `cortex.pipeline.stages.documentation`
- `cortex.pipeline.stages.lint`
- `cortex.pipeline.stages.security`
- `cortex.pipeline.stages.test`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 168.
Docstrings de símbolos públicos:
- `PipelineContext.from_pr_context`: Build a PipelineContext from an existing PRContext model.
- `PipelineContext.from_env`: Build a PipelineContext from GitHub Actions environment variables.
- `PipelineContext.get_stage_output`: Retrieve a value written by a previous stage.
- `PipelineContext.set_stage_output`: Write a value to the shared inter-stage communication dict.

---
Fuente: código de `cortex/pipeline/domain/context.py` (AST + grafo de imports internos). No se usó documentación previa.
