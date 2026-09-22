# cortex/ide/prompts.py

## Qué tiene adentro

- **Ruta de código:** `cortex/ide/prompts.py` (142 líneas).
- **Módulo Python:** `cortex.ide.prompts`.
- **Docstring del módulo:** cortex.ide.prompts ------------------ Centralized prompt generation for Cortex agent profiles.
- **Funciones de módulo:**
  - `split_markdown_frontmatter(content)` — Split optional YAML frontmatter from markdown content.
  - `strip_markdown_frontmatter(content)` — Return markdown content without the leading YAML frontmatter.
  - `get_skill_prompt(project_root, skill_name)` — Read a skill prompt from the workspace skills directory.
  - `get_subagent_prompt(project_root, subagent_name)` — Read a subagent prompt from the workspace subagents directory.
  - `get_available_subagents(project_root)` — Discover which subagents actually exist on disk.
  - `build_all_prompts(project_root)` — Build the full set of Cortex prompts for injection.
  - `build_autopilot_prompts(project_root)` — Build Autopilot-specific prompts for injection.

## Para qué sirve

cortex.ide.prompts
------------------
Centralized prompt generation for Cortex agent profiles.

Reads the actual skill files from the workspace layout (using
WorkspaceLayout to resolve paths) as the single source of truth.
Never hardcodes prompt content — always derives from the real files on disk.

EPIC 5: All path resolution now goes through WorkspaceLayout so that
new-layout projects (where skills/subagents live under
repo_root/.cortex/) and legacy projects both work correctly.

## Relaciones

### Recibe de

- `cortex.workspace.layout` (WorkspaceLayout)
- Dependencias externas/stdlib: `__future__`, `pathlib`

### Envía a

- `cortex.ide`
- `cortex.ide.adapters.claude_code`
- `cortex.ide.adapters.cursor`
- `cortex.ide.adapters.vscode`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 142.
Docstrings de símbolos públicos:
- `split_markdown_frontmatter`: Split optional YAML frontmatter from markdown content.
- `strip_markdown_frontmatter`: Return markdown content without the leading YAML frontmatter.
- `get_skill_prompt`: Read a skill prompt from the workspace skills directory.
- `get_subagent_prompt`: Read a subagent prompt from the workspace subagents directory.
- `get_available_subagents`: Discover which subagents actually exist on disk.
- `build_all_prompts`: Build the full set of Cortex prompts for injection.
- `build_autopilot_prompts`: Build Autopilot-specific prompts for injection.

---
Fuente: código de `cortex/ide/prompts.py` (AST + grafo de imports internos). No se usó documentación previa.
