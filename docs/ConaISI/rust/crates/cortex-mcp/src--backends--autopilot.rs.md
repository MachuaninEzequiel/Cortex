# rust/crates/cortex-mcp/src/backends/autopilot.rs

## Qué tiene adentro

`NativeAutopilotBackend` con `Mutex<Option<AutopilotService>>` lazy (`from_project_root`). Traduce outcomes a StartData/PreflightData/etc.

## Para qué sirve

Tools MCP autopilot sobre la capa de decisión nativa.

## Relaciones

### Recibe de

- `cortex_autopilot::AutopilotService` + `AutopilotMode`.

### Envía a

- handlers_autopilot.

### Notas de implementación observadas en el código

Poisoned mutex → AutopilotToolError Other.
