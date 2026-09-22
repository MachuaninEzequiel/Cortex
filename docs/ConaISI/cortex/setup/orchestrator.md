# cortex/setup/orchestrator.py

## Qué tiene adentro

- **Ruta de código:** `cortex/setup/orchestrator.py` (659 líneas).
- **Módulo Python:** `cortex.setup.orchestrator`.
- **Docstring del módulo:** cortex.setup.orchestrator ------------------------- Orchestration engine for modular setup (agent, pipeline, full).
- **Clases definidas:**
  - `SetupMode` (str, Enum)
  - `SetupOrchestrator`
    - Runs the setup pipeline based on mode and reports results.
    - Métodos públicos/especiales: `__init__`, `run`
    - Métodos internos: `_rel_path`, `_run_enterprise_flow`, `_simulate_flow`, `_run_agent_flow`, `_run_pipeline_flow`, `_run_full_flow`, `_update_gitignore`, `_run_webgraph_flow`, `_create_directories`, `_create_config`, `_create_vault_docs`, `_create_enterprise_org_config`, `_create_enterprise_workspace`, `_simulate_enterprise_flow`, `_create_enterprise_vault`, `_create_workflows`, `_create_devsecdocops_script`, `_create_agent_guidelines`, `_install_skills`, `_check_vault_pipeline_interactive`…
- **Funciones de módulo:**
  - `format_summary(summary)`

## Para qué sirve

cortex.setup.orchestrator
-------------------------
Orchestration engine for modular setup (agent, pipeline, full).

EPIC 4: All file creation now writes exclusively through
``WorkspaceLayout`` so that a brand-new project generates the
new-layout structure (``.cortex/`` as workspace root) while
legacy projects keep working through compatibility dual paths.

## Relaciones

### Recibe de

- `cortex.enterprise.config` (render_enterprise_config_yaml)
- `cortex.enterprise.models` (EnterpriseOrgConfig)
- `cortex.setup.cortex_workspace` (ensure_cortex_workspace)
- `cortex.setup.detector` (ProjectContext, ProjectDetector)
- `cortex.setup.enterprise_presets` (resolve_enterprise_setup)
- `cortex.setup.templates` (DEVSECDOCSOPS_SCRIPT, render_architecture_md, render_cd_deploy, render_ci_enterprise_governance, render_ci_feature, render_ci_pull_request, render_config_yaml, render_context_md, render_decisions_md, render_enterprise_runbook_md, render_enterprise_vault_readme, render_git_vault_policy_md…)
- `cortex.workspace.layout` (WorkspaceLayout)
- Dependencias externas/stdlib: `typer`, `__future__`, `enum`, `pathlib`, `typing`

### Envía a

- `cortex.setup`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 659.
Docstrings de símbolos públicos:
- `SetupOrchestrator.run`: Execute the setup pipeline based on mode. Returns a summary dict.

---
Fuente: código de `cortex/setup/orchestrator.py` (AST + grafo de imports internos). No se usó documentación previa.
