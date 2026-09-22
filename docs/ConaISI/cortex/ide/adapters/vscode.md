# cortex/ide/adapters/vscode.py

## Qué tiene adentro

- **Ruta de código:** `cortex/ide/adapters/vscode.py` (221 líneas).
- **Módulo Python:** `cortex.ide.adapters.vscode`.
- **Clases definidas:**
  - `VSCodeAdapter` (IDEAdapter)
    - Métodos públicos/especiales: `name`, `display_name`, `get_config_paths`, `inject_profiles`, `inject_mcp`, `uninstall`
- **Funciones de módulo:**
  - `_render_vscode_agent(frontmatter, header, body)`
  - `_render_claude_agent(name, description, header, body)`
- **Constantes / símbolos de módulo:** `_VSCODE_TOP_AGENTS`, `_CLAUDE_SUBAGENTS`

## Para qué sirve

Define VSCodeAdapter. No hay docstring de módulo; el propósito se infiere de las clases y métodos listados.

## Relaciones

### Recibe de

- `cortex.ide.base` (IDEAdapter, _backup_file, _deep_merge_dict, _generate_autogen_header)
- `cortex.ide.prompts` (get_subagent_prompt, strip_markdown_frontmatter)
- Dependencias externas/stdlib: `contextlib`, `json`, `logging`, `__future__`, `pathlib`, `typing`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 221.
Docstrings de símbolos públicos:
- `VSCodeAdapter.uninstall`: Eliminar lo inyectado por Cortex en VS Code:

---
Fuente: código de `cortex/ide/adapters/vscode.py` (AST + grafo de imports internos). No se usó documentación previa.
