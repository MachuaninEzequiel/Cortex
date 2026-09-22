# cortex/pipeline/stages/security.py

## Qué tiene adentro

- **Ruta de código:** `cortex/pipeline/stages/security.py` (173 líneas).
- **Módulo Python:** `cortex.pipeline.stages.security`.
- **Docstring del módulo:** cortex.pipeline.stages.security --------------------------------- SecurityStage — dependency vulnerability audit gate.
- **Clases definidas:**
  - `SecurityStage`
    - Dependency vulnerability audit stage (SCA — Software Composition Analysis).
    - Métodos públicos/especiales: `__init__`, `name`, `stage_type`, `block_on_failure`, `execute`
    - Métodos internos: `_is_python_project`, `_parse_findings`

## Para qué sirve

cortex.pipeline.stages.security
---------------------------------
SecurityStage — dependency vulnerability audit gate.

Runs ``pip-audit`` (Python) or ``npm audit`` (JS/TS) against the
project's dependencies and blocks the pipeline on HIGH/CRITICAL findings.

Integration
-----------
The stage is provider-agnostic: it runs ``subprocess`` commands locally
or in any CI environment (GitHub Actions, GitLab CI, etc.) and returns
a typed ``StageResult`` that the orchestrator uses for gate enforcement.

## Relaciones

### Recibe de

- `cortex.pipeline.domain.context` (PipelineContext)
- `cortex.pipeline.domain.types` (StageResult, StageStatus, StageType)
- Dependencias externas/stdlib: `logging`, `subprocess`, `time`, `__future__`, `typing`

### Envía a

- `cortex.pipeline.stages`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 173.
Docstrings de símbolos públicos:
- `SecurityStage.execute`: Run the appropriate audit command based on detected project type.

---
Fuente: código de `cortex/pipeline/stages/security.py` (AST + grafo de imports internos). No se usó documentación previa.
