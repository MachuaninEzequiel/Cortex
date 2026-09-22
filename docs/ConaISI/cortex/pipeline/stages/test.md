# cortex/pipeline/stages/test.py

## Qué tiene adentro

- **Ruta de código:** `cortex/pipeline/stages/test.py` (200 líneas).
- **Módulo Python:** `cortex.pipeline.stages.test`.
- **Docstring del módulo:** cortex.pipeline.stages.test ----------------------------- TestStage — test suite execution and coverage enforcement gate.
- **Clases definidas:**
  - `TestStage`
    - Test suite execution and coverage enforcement stage.
    - Métodos públicos/especiales: `__init__`, `name`, `stage_type`, `block_on_failure`, `execute`
    - Métodos internos: `_detect_command`, `_extract_coverage`

## Para qué sirve

cortex.pipeline.stages.test
-----------------------------
TestStage — test suite execution and coverage enforcement gate.

Runs pytest (Python) or the project's test script (Node/other) and
enforces a minimum coverage threshold. Blocks the pipeline if tests
fail or coverage is below the configured minimum.

## Relaciones

### Recibe de

- `cortex.pipeline.domain.context` (PipelineContext)
- `cortex.pipeline.domain.types` (StageResult, StageStatus, StageType)
- Dependencias externas/stdlib: `logging`, `re`, `subprocess`, `time`, `__future__`

### Envía a

- `cortex.pipeline.stages`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 200.
Docstrings de símbolos públicos:
- `TestStage.execute`: Run the test suite and check coverage.

---
Fuente: código de `cortex/pipeline/stages/test.py` (AST + grafo de imports internos). No se usó documentación previa.
