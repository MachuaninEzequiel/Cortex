# rust/crates/cortex-setup/src/ide/adapters/opencode.rs

## Qué tiene adentro

`OpenCodeAdapter`. Skills `~/.config/opencode/skills/`, subagents, `opencode.json` campo `permission` allow|ask|deny. MCP bajo clave `mcp`. Tools MCP no se declaran (descubrimiento dinámico). `needs_wsl_shielding` posible.

## Para qué sirve

OpenCode (target).

## Relaciones

### Recibe de

- mcp_command + deep_merge_dict.

### Envía a

- HOME config opencode + project.

### Notas de implementación observadas en el código

canonical_tools traduce MCP a None para este IDE.
