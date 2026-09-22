# cortex/pipeline/domain/types.py

## Qué tiene adentro

- **Ruta de código:** `cortex/pipeline/domain/types.py` (184 líneas).
- **Módulo Python:** `cortex.pipeline.domain.types`.
- **Docstring del módulo:** cortex.pipeline.domain.types ----------------------------- Core value types for the DevSecDocOps pipeline.
- **Clases definidas:**
  - `StageType` (Enum)
    - Semantic classification of pipeline stages.
  - `StageStatus` (Enum)
    - Execution outcome of a single pipeline stage.
  - `StageResult`
    - Immutable record of a single stage's execution outcome.
    - Métodos públicos/especiales: `passed`, `failed`, `icon`, `to_dict`
  - `PipelineReport`
    - Aggregated result of a full pipeline run.
    - Métodos públicos/especiales: `passed`, `failed_stages`, `total_duration_ms`, `summary`, `to_markdown`, `to_dict`

## Para qué sirve

cortex.pipeline.domain.types
-----------------------------
Core value types for the DevSecDocOps pipeline.

All types are immutable (frozen dataclasses or Pydantic models).
No I/O, no side effects — safe to use anywhere.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `__future__`, `dataclasses`, `datetime`, `enum`, `typing`

### Envía a

- `cortex.pipeline`
- `cortex.pipeline.domain.protocols`
- `cortex.pipeline.orchestrator`
- `cortex.pipeline.runners.github`
- `cortex.pipeline.stages.documentation`
- `cortex.pipeline.stages.lint`
- `cortex.pipeline.stages.security`
- `cortex.pipeline.stages.test`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 184.
Docstrings de símbolos públicos:
- `StageResult.icon`: Emoji icon for display in PR comments / logs.
- `StageResult.to_dict`: Serialize to a JSON-safe dict (for artifacts / upload).
- `PipelineReport.passed`: True if all non-skipped stages passed.
- `PipelineReport.summary`: Human-readable single-line summary for logs.
- `PipelineReport.to_markdown`: Render pipeline results as a Markdown table for PR comments.
- `PipelineReport.to_dict`: Serialize for JSON artifact upload.

---
Fuente: código de `cortex/pipeline/domain/types.py` (AST + grafo de imports internos). No se usó documentación previa.
