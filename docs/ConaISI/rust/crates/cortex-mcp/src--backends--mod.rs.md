# rust/crates/cortex-mcp/src/backends/mod.rs

## Qué tiene adentro

Reexporta módulos nativos. Helpers: `repo_root()` (WorkspaceLayout.discover(cwd).repo_root), `read_config_yaml` (`.cortex/config.yaml` o Null), `vault_path` (`semantic.vault_path` default `"vault"`, resuelto con layout).

## Para qué sirve

Glue de producción: los handlers formatean; los backends proveen datos reales.

## Relaciones

### Recibe de

- cwd del proceso MCP (`mcp.json` cwd del proyecto).
- `cortex_workspace::WorkspaceLayout`.

### Envía a

- Cada `Native*Backend`.

### Notas de implementación observadas en el código

Antes `server.new()` dejaba backends en None; el binario CLI los inyecta.
