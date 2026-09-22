# rust/crates/cortex-cli/src/commands/ide_cmd.rs

## Qué tiene adentro

`ide list|setup|remove|status`. Registry: TARGET (claude_code, codex, opencode, pi), COMMUNITY (claude_desktop, cursor, vscode, windsurf), EXPERIMENTAL (antigravity, hermes, zed). Aliases (claude→claude_code, code→vscode, ...). Tabla rich 80 col. Setup inyecta perfiles+MCP (`inject_profiles`/`inject_mcp`); **no** instala hooks.

## Para qué sirve

Inyectar Cortex en IDEs.

## Relaciones

### Recibe de

- `cortex_setup::ide::{all_adapters, prompts, IdeCtx}`.
- `HookInstaller` solo para status.

### Envía a

- Archivos de config de cada IDE + reports.

### Notas de implementación observadas en el código

VALIDATED_IDES CLI: claude_code, cursor, opencode, pi, codex (más amplio que canonical_tools que solo valida traducción claude_code/opencode).
