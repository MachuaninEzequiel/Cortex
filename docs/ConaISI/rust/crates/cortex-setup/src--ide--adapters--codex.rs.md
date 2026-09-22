# rust/crates/cortex-setup/src/ide/adapters/codex.rs

## Qué tiene adentro

`CodexAdapter`. AGENTS.md en project root con marcadores. MCP TOML `.codex/config.toml` `[mcp_servers.cortex]`. Trust en `~/.codex/config.toml` (CODEX_HOME), marcadores por path (multi-repo). Sin subagents/skills custom: guidance inline. Escaneo de spans en vez de regex DOTALL.

## Para qué sirve

Codex CLI (OpenAI).

## Relaciones

### Recibe de

- IdeCtx home/now; `shutil.which` via PATH.

### Envía a

- AGENTS.md, configs TOML.

### Notas de implementación observadas en el código

normcase identidad en Linux.
