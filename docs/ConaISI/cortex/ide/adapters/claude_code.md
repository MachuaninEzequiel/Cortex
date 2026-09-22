# cortex/ide/adapters/claude_code.py

## Qué tiene adentro

- **Ruta de código:** `cortex/ide/adapters/claude_code.py` (477 líneas).
- **Módulo Python:** `cortex.ide.adapters.claude_code`.
- **Clases definidas:**
  - `ClaudeCodeAdapter` (IDEAdapter)
    - Métodos públicos/especiales: `name`, `display_name`, `get_config_paths`, `inject_profiles`, `inject_mcp`, `uninstall`
- **Funciones de módulo:**
  - `_render_claude_markdown(frontmatter, header, body)`
  - `_parse_canonical_tools(frontmatter_text)` — Parse el campo ``tools:`` del frontmatter de un prompt canonico.
  - `_claude_workflow_doc(header)` — Contenido EXACTO que ``inject_profiles`` escribe en ``CLAUDE.md``.

## Para qué sirve

Define ClaudeCodeAdapter. No hay docstring de módulo; el propósito se infiere de las clases y métodos listados.

## Relaciones

### Recibe de

- `cortex.ide.base` (IDEAdapter, _backup_file, _deep_merge_dict, _generate_autogen_header, has_marker_block, is_content_identical_to_bundle, strip_marker_blocks)
- `cortex.ide.canonical_tools` (translate_list)
- `cortex.ide.prompts` (get_subagent_prompt, split_markdown_frontmatter, strip_markdown_frontmatter)
- Dependencias externas/stdlib: `contextlib`, `json`, `__future__`, `pathlib`, `typing`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 477.
Docstrings de símbolos públicos:
- `ClaudeCodeAdapter.uninstall`: Remove Cortex artifacts from the Claude Code project (Fase 2).

---
Fuente: código de `cortex/ide/adapters/claude_code.py` (AST + grafo de imports internos). No se usó documentación previa.
