# cortex/pipeline/domain/protocols.py

## Qué tiene adentro

- **Ruta de código:** `cortex/pipeline/domain/protocols.py` (78 líneas).
- **Módulo Python:** `cortex.pipeline.domain.protocols`.
- **Docstring del módulo:** cortex.pipeline.domain.protocols ---------------------------------- The PipelineStage Protocol — the contract that every stage must satisfy.
- **Clases definidas:**
  - `PipelineStage` (Protocol)
    - Structural protocol for all DevSecDocOps pipeline stages.
    - Métodos públicos/especiales: `name`, `stage_type`, `block_on_failure`, `execute`

## Para qué sirve

cortex.pipeline.domain.protocols
----------------------------------
The PipelineStage Protocol — the contract that every stage must satisfy.

Using ``typing.Protocol`` (structural subtyping) means:
1. Stages don't need to inherit from a base class.
2. Any class with the right shape satisfies the contract automatically.
3. ``runtime_checkable`` enables isinstance() validation at startup.

Gate configuration
------------------
Each stage declares whether it should block the pipeline on failure
via ``block_on_failure``. The orchestrator reads this to decide
whether to abort or continue after a failed stage.

## Relaciones

### Recibe de

- `cortex.pipeline.domain.types` (StageResult, StageType)
- Dependencias externas/stdlib: `__future__`, `typing`

### Envía a

- `cortex.pipeline`
- `cortex.pipeline.orchestrator`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 78.
Docstrings de símbolos públicos:
- `PipelineStage.name`: Human-readable stage name (e.g. 'Run Tests').
- `PipelineStage.stage_type`: Semantic classification used by gate rules and runners.
- `PipelineStage.block_on_failure`: If True, the orchestrator will abort the pipeline when this
- `PipelineStage.execute`: Run the stage logic and return an immutable result.

---
Fuente: código de `cortex/pipeline/domain/protocols.py` (AST + grafo de imports internos). No se usó documentación previa.
