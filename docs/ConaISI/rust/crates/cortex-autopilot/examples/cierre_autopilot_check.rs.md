# rust/crates/cortex-autopilot/examples/cierre_autopilot_check.rs

## Qué tiene adentro

Archivo de 836 líneas.
Checker CIERRE T3-PAR — paridad byte-a-byte del autopilot service + tools MCP ×5 contra `bench/parity/.p12-cierre-autopilot/golden_cierre_autopilot.txt` (oráculo: service.py + `_dispatch_tool_sync` Python REALES con sesiones fixture reales).  Uso: cargo run -p cortex-autopilot --example cierre_autopilot_check -- <golden_dir>  Reproduce las partes [A] SERVICE y [B] MCP del golden (hasta el marcador `[[CLI-PART]]`); la parte [C] CLI es dual py-vs-rs dentro del propio golden (patrón P12B-8).

## Para qué sirve

Checker CIERRE T3-PAR — paridad byte-a-byte del autopilot service + tools MCP ×5 contra `bench/parity/.p12-cierre-autopilot/golden_cierre_autopilot.txt` (oráculo: service.py + `_dispatch_tool_sync` Python REALES con sesiones fixture reales).  Uso: cargo run -p cortex-autopilot --example cierre_autopilot_check -- <golden_dir>  Reproduce las partes [A] SERVICE y [B] MCP del golden (hasta el marcador `[[CLI-PART]]`); la parte [C] CLI es dual py-vs-rs dentro del propio golden (patrón P12B-8).

## Relaciones

### Recibe de

- `use cortex_app::session::SessionStorage`
- `use cortex_autopilot::policies::AutopilotMode`
- `use cortex_autopilot::service::{AutopilotService, ServiceError, StatusOutcome}`
- `use cortex_mcp::handlers_autopilot::{`
- `use cortex_mcp::server::CortexMcpServer`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-autopilot/examples/cierre_autopilot_check.rs`. 836 líneas.
