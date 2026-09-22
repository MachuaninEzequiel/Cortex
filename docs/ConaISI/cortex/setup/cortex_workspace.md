# cortex/setup/cortex_workspace.py

## Qué tiene adentro

- **Ruta de código:** `cortex/setup/cortex_workspace.py` (208 líneas).
- **Módulo Python:** `cortex.setup.cortex_workspace`.
- **Docstring del módulo:** cortex.setup.cortex_workspace ----------------------------- Generate the Cortex workspace structure used by Release 2:
- **Funciones de módulo:**
  - `_read_workspace_file(nombre)` — Lee un archivo de workspace desde ``workspace_files/`` (fuente única V8).
  - `_autopilot_skills_dir()` — Return the package directory containing Autopilot skill templates.
  - `render_system_prompt()`
  - `render_agent_overview()`
  - `render_cortex_sync_skill()`
  - `render_cortex_sddwork_skill()`
  - `render_cortex_documenter_skill()`
  - `render_subagent_explorer()`
  - `render_subagent_implementer()`
  - `render_subagent_documenter()`
  - `render_subagent_designer()`
  - `_obsidian_skill_files()` — Return the Obsidian formatting skills, hardcoded into ``.cortex/``.
  - `workspace_file_map()`
  - `autopilot_file_map()` — Return Autopilot skill files to install into the workspace.
  - `ensure_cortex_workspace(root)` — Create the Release 2 Cortex workspace files inside ``root``.
- **Constantes / símbolos de módulo:** `_WORKSPACE_FILES_DIR`

## Para qué sirve

cortex.setup.cortex_workspace
-----------------------------
Generate the Cortex workspace structure used by Release 2:

- .cortex/system-prompt.md
- .cortex/skills/cortex-sync.md
- .cortex/skills/cortex-SDDwork.md
- .cortex/subagents/*.md
- .cortex/AGENT.md
- .cortex/workspace.yaml   (layout_version: 2)

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `__future__`, `pathlib`

### Envía a

- `cortex.setup`
- `cortex.setup.orchestrator`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 208.
Docstrings de símbolos públicos:
- `autopilot_file_map`: Return Autopilot skill files to install into the workspace.
- `ensure_cortex_workspace`: Create the Release 2 Cortex workspace files inside ``root``.

---
Fuente: código de `cortex/setup/cortex_workspace.py` (AST + grafo de imports internos). No se usó documentación previa.
