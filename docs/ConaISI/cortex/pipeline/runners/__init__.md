# cortex/pipeline/runners/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/pipeline/runners/__init__.py` (17 líneas).
- **Módulo Python:** `cortex.pipeline.runners`.
- **Docstring del módulo:** cortex.pipeline.runners ------------------------ CI/CD provider adapters for the Cortex pipeline.
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.pipeline.runners
------------------------
CI/CD provider adapters for the Cortex pipeline.

Runners translate a list of PipelineStage definitions into
provider-specific configuration (YAML workflows, API calls, etc.).

Available runners
-----------------
- ``GitHubActionsRunner`` → generates GitHub Actions workflow YAML

## Relaciones

### Recibe de

- `cortex.pipeline.runners.github` (GitHubActionsRunner)

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 17.
Reexportes observados:
- cortex.pipeline.runners.github: GitHubActionsRunner

---
Fuente: código de `cortex/pipeline/runners/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
