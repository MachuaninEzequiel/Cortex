# cortex/ide/adapters/cursor.py

## Qué tiene adentro

- **Ruta de código:** `cortex/ide/adapters/cursor.py` (366 líneas).
- **Módulo Python:** `cortex.ide.adapters.cursor`.
- **Docstring del módulo:** cortex.ide.adapters.cursor — Cursor IDE adapter.
- **Clases definidas:**
  - `CursorAdapter` (IDEAdapter)
    - Métodos públicos/especiales: `name`, `display_name`, `get_config_paths`, `inject_profiles`, `inject_mcp`, `uninstall`
- **Funciones de módulo:**
  - `_render_cursor_skill(skill_name, description, autogen_header, body)` — Render a Cursor 2.4+ skill ``SKILL.md`` file.
  - `_render_cursor_subagent(name, description, readonly, autogen_header, body)` — Render un subagent file en formato Cursor 2.4+.
- **Constantes / símbolos de módulo:** `_CORTEX_SUBAGENTS`, `_CORTEX_SLASH_SKILLS`

## Para qué sirve

cortex.ide.adapters.cursor — Cursor IDE adapter.

Rediseno completo en Fase 4 del plan multi-IDE & MCP hardening (2026-05-15)
basado en validacion contra documentacion oficial de Cursor 2.4+:

    https://cursor.com/docs/subagents

Decision 3 firmada del creador: usar los 3 subagents canonicos reales
(``cortex-code-explorer``, ``cortex-code-implementer``, ``cortex-documenter``)
en ``.cursor/agents/``. Eliminado el adapter hibrido pre-2.4 con
``cortex-SDDwork-cursor.md`` (variante por IDE en la SSoT que violaba el
principio rector #1).

Layout escrito por este adapter:

    .cursor/
      agents/
        cortex-code-explorer.md       ← subagent canonico
        cortex-code-implementer.md    ← subagent canonico
        cortex-documenter.md          ← subagent canonico
      mcp.json                        ← MCP server registration

Cursor frontmatter campos soportados (segun docs oficiales 2026):

- ``name``: identificador (default: derivado del filename)
- ``description``: cuando usar el subagent
- ``model``: ``inherit`` por default
- ``readonly``: bool, default false
- ``is_background``: bool, default false

NO se declara ``tools:`` en frontmatter — Cursor subagents heredan TODAS
las tools del padre. Esto es el comportamiento documentado oficialmente.

## Relaciones

### Recibe de

- `cortex.ide.base` (IDEAdapter, _backup_file, _deep_merge_dict, _generate_autogen_header)
- `cortex.ide.prompts` (get_skill_prompt, get_subagent_prompt, strip_markdown_frontmatter)
- Dependencias externas/stdlib: `contextlib`, `json`, `logging`, `__future__`, `pathlib`, `typing`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 366.
Docstrings de símbolos públicos:
- `CursorAdapter.inject_profiles`: Inyecta los subagents canónicos en ``.cursor/agents/`` y los 3
- `CursorAdapter.inject_mcp`: Inject MCP server configuration for Cursor.
- `CursorAdapter.uninstall`: Eliminar lo inyectado por Cortex en Cursor:

---
Fuente: código de `cortex/ide/adapters/cursor.py` (AST + grafo de imports internos). No se usó documentación previa.
