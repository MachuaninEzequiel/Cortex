# cortex/pipeline/orchestrator.py

## Qué tiene adentro

- **Ruta de código:** `cortex/pipeline/orchestrator.py` (117 líneas).
- **Módulo Python:** `cortex.pipeline.orchestrator`.
- **Docstring del módulo:** cortex.pipeline.orchestrator ----------------------------- PipelineOrchestrator — executes stages in order, enforces gates.
- **Clases definidas:**
  - `PipelineOrchestrator`
    - Executes a sequence of pipeline stages and returns a PipelineReport.
    - Métodos públicos/especiales: `__init__`, `run`

## Para qué sirve

cortex.pipeline.orchestrator
-----------------------------
PipelineOrchestrator — executes stages in order, enforces gates.

The orchestrator is the single coordination point for a pipeline run.
It knows about:
- Which stages to run (injected as a list)
- Whether to abort when a blocking stage fails (gate enforcement)
- How to collect and aggregate results into a PipelineReport

It does NOT know about:
- CI providers (that's the runners' job)
- Business logic of individual stages (that's each stage's job)
- How results are displayed (that's the report's job)

## Relaciones

### Recibe de

- `cortex.pipeline.domain.context` (PipelineContext)
- `cortex.pipeline.domain.protocols` (PipelineStage)
- `cortex.pipeline.domain.types` (PipelineReport, StageResult, StageStatus)
- Dependencias externas/stdlib: `logging`, `__future__`, `datetime`

### Envía a

- `cortex.pipeline`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 117.
Docstrings de símbolos públicos:
- `PipelineOrchestrator.run`: Execute all stages and return a consolidated PipelineReport.

---
Fuente: código de `cortex/pipeline/orchestrator.py` (AST + grafo de imports internos). No se usó documentación previa.
