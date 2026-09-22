# rust/crates/cortex-setup/src/ide/adapters/claude_code.rs

## Qué tiene adentro

`ClaudeCodeAdapter`. Skills slash `.claude/skills/cortex-*/SKILL.md`, subagents `.claude/agents/cortex-*.md` con tools PascalCase/`mcp__cortex__`, workflow CLAUDE.md, MCP `.mcp.json` + `.claude/settings.json`.

## Para qué sirve

Inyección Claude Code (target).

## Relaciones

### Recibe de

- Prompts + canonical_tools::translate_list + base helpers.

### Envía a

- Árbol `.claude/` y CLAUDE.md.

### Notas de implementación observadas en el código

Header autogen dentro de comentario HTML.
