# rust/crates/cortex-cli/src/commands/mcp_cmd.rs

## Qué tiene adentro

`mcp-server` / `mcp-serve --stdio` (único transporte). Construye `CortexMcpServer`, setea `project_root`, inyecta NativeSessions/Spec/Finish/Docs/Autopilot; Search si `NativeSearchBackend::open` ok. `serve_stdio_blocking`.

## Para qué sirve

Entrypoint MCP que los adapters IDE configuran como `"command": "cortex-cli", "args": ["mcp-server", "--stdio"]`.

## Relaciones

### Recibe de

- `cortex_mcp::{server, backends}`.

### Envía a

- stdio JSON-RPC MCP.

### Notas de implementación observadas en el código

Si search falla, stderr `"mcp: search backend no disponible"` y el server igual arranca.
