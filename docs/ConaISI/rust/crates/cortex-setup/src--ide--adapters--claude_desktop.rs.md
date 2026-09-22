# rust/crates/cortex-setup/src/ide/adapters/claude_desktop.rs

## Qué tiene adentro

`ClaudeDesktopAdapter`. Community. Inyecta config MCP de escritorio Claude (paths bajo home).

## Para qué sirve

Claude Desktop.

## Relaciones

### Recibe de

- IdeCtx.home + mcp_command.

### Envía a

- Archivos de config de Claude Desktop.

### Notas de implementación observadas en el código

Struct unitario; lógica en impl IdeAdapter.
