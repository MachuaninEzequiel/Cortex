# rust/crates/cortex-setup/src/ide/adapters/cursor.rs

## Qué tiene adentro

`CursorAdapter`. Subagents `.cursor/agents/`, skills `.cursor/skills/<n>/SKILL.md`. MCP user-level `~/.cursor/mcp.json`. Frontmatter name/description/model inherit/readonly. **No** declara `tools:` (heredan todas las del padre).

## Para qué sirve

Cursor 2.4+ (community, validado en CLI).

## Relaciones

### Recibe de

- get_skill_prompt / get_subagent_prompt.

### Envía a

- `.cursor/` y mcp.json de usuario.

### Notas de implementación observadas en el código

Spec `_CORTEX_SUBAGENTS` declarativa.
