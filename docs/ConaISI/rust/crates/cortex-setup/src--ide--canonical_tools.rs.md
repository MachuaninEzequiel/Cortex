# rust/crates/cortex-setup/src/ide/canonical_tools.rs

## Qué tiene adentro

`CANONICAL_TOOLS` (fs, shell, MCP Cortex, session, review, design, tasks). `VALIDATED_IDES = [claude_code, opencode]`. `translate` / `translate_list`. `TranslateError::{UnknownCanonicalTool, UnvalidatedIde}`.

Traducción: claude_code PascalCase + `mcp__cortex__`; opencode lowercase y MCP = None (omitir).

## Para qué sirve

Traducir nombres canónicos SOLO en frontmatter `tools:` (nunca el cuerpo del prompt).

## Relaciones

### Recibe de

- Adapters (claude_code principalmente).

### Envía a

- Frontmatter de skills/subagents.

### Notas de implementación observadas en el código

`cortex_delegate_task` eliminado. IDEs no validados → error intencional.
