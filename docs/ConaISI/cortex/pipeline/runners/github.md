# cortex/pipeline/runners/github.py

## Qué tiene adentro

- **Ruta de código:** `cortex/pipeline/runners/github.py` (333 líneas).
- **Módulo Python:** `cortex.pipeline.runners.github`.
- **Docstring del módulo:** cortex.pipeline.runners.github -------------------------------- GitHubActionsRunner — generates GitHub Actions workflow YAML from a pipeline stage configuration.
- **Clases definidas:**
  - `GitHubActionsRunner`
    - Generates GitHub Actions workflow YAML for the DevSecDocOps pipeline.
    - Métodos públicos/especiales: `__init__`, `generate_pr_workflow`
    - Métodos internos: `_build_steps`, `_step_security`, `_step_lint`, `_step_test`, `_step_documentation`

## Para qué sirve

cortex.pipeline.runners.github
--------------------------------
GitHubActionsRunner — generates GitHub Actions workflow YAML from a
pipeline stage configuration.

This is a pure generator: it takes a list of stage types and a
pipeline config dict, and produces valid YAML that can be written
to ``.github/workflows/``. No I/O of its own.

Design
------
The runner knows the GitHub Actions primitives (jobs, steps, secrets,
caching) but knows nothing about business logic. It maps StageType
to the appropriate shell commands via the project context.

Extensibility
-------------
To add a new CI provider (GitLab CI, Azure DevOps, Jenkins):
1. Create ``cortex/pipeline/runners/gitlab.py`` with a ``GitLabCIRunner``.
2. Implement ``generate_workflow(stages, config) -> str``.
3. Register it in ``runners/__init__.py``.
No changes needed anywhere else.

## Relaciones

### Recibe de

- `cortex.pipeline.domain.types` (StageType)
- Dependencias externas/stdlib: `__future__`

### Envía a

- `cortex.pipeline.runners`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 333.
Docstrings de símbolos públicos:
- `GitHubActionsRunner.generate_pr_workflow`: Generate a complete GitHub Actions workflow YAML for PR validation.

---
Fuente: código de `cortex/pipeline/runners/github.py` (AST + grafo de imports internos). No se usó documentación previa.
