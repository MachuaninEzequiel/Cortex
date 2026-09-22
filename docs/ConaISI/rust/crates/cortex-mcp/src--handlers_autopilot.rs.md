# rust/crates/cortex-mcp/src/handlers_autopilot.rs

## Qué tiene adentro

`AutopilotToolError`, mirrors Start/Preflight/Checkpoint/Finish/Status. Trait `AutopilotBackend`. Handlers `*_text` para las 5 tools autopilot.

## Para qué sirve

Familia MCP autopilot.

## Relaciones

### Recibe de

- Args session_id/mode/user_request/files.
- `NativeAutopilotBackend` → `AutopilotService`.

### Envía a

- JSON de outcomes al agente.

### Notas de implementación observadas en el código

Traduce errores de servicio a kind/message estables.
