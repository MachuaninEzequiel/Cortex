# rust/crates/cortex-mcp/Cargo.toml

## Qué tiene adentro

Manifiesto P9. Comentarios de reglas: contrato `list_tools.json` (32 tools, server_version 2.2); dispatcher replica `_TOOL_ROUTES` + inline `cortex_sync_vault` + mensaje `"Herramienta desconocida: X"`; tools sin backend nativo → fallo explícito (patrón P6).

Deps: rmcp, serde, serde_json preserve_order, tokio, cortex-{setup,app,workspace,services,autopilot,embed}, serde_yaml, chrono, regex.

## Para qué sirve

Compilar el servidor MCP como librería (el binario stdio lo lanza cortex-cli).

## Relaciones

### Recibe de

- Workspace deps y crates de dominio.

### Envía a

- `cortex-cli` (`mcp_cmd`, `finish_cmd` usa `NativeFinishBackend`).
- `cortex-autopilot` (dependencia inversa en workspace: autopilot lista cortex-mcp).

### Notas de implementación observadas en el código

`regex` justificado por keywords/candidate files del mixín search; ya estaba en el lock.
