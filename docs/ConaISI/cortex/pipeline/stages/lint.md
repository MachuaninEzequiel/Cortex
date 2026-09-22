# cortex/pipeline/stages/lint.py

## Qué tiene adentro

- **Ruta de código:** `cortex/pipeline/stages/lint.py` (167 líneas).
- **Módulo Python:** `cortex.pipeline.stages.lint`.
- **Docstring del módulo:** cortex.pipeline.stages.lint ----------------------------- LintStage — static analysis and code style gate.
- **Clases definidas:**
  - `LintStage`
    - Static analysis / code style enforcement stage.
    - Métodos públicos/especiales: `__init__`, `name`, `stage_type`, `block_on_failure`, `execute`
    - Métodos internos: `_detect_command`
- **Constantes / símbolos de módulo:** `_DEFAULT_COMMANDS`

## Para qué sirve

cortex.pipeline.stages.lint
-----------------------------
LintStage — static analysis and code style gate.

Runs the project's linter (Ruff for Python, ESLint for JS/TS, etc.)
and reports results as a typed StageResult.

The stage auto-detects the project language from the changed files
or falls back to a user-provided command.

## Relaciones

### Recibe de

- `cortex.pipeline.domain.context` (PipelineContext)
- `cortex.pipeline.domain.types` (StageResult, StageStatus, StageType)
- Dependencias externas/stdlib: `logging`, `subprocess`, `time`, `__future__`

### Envía a

- `cortex.pipeline.stages`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 167.
Docstrings de símbolos públicos:
- `LintStage.execute`: Run the lint command and parse its output.

---
Fuente: código de `cortex/pipeline/stages/lint.py` (AST + grafo de imports internos). No se usó documentación previa.
