# rust/crates/cortex-autopilot/src/lifecycle.rs

## Qué tiene adentro

Puerto de `cortex.autopilot.lifecycle`: tipos request/result de los flujos del servicio. La orquestación real queda tras el motor de sesiones.
Archivo de 25 líneas.
Símbolos públicos observados:
- `pub struct AutopilotStartRequest`
- `pub struct PreflightResult`
- `pub type SystemClockAlias = cortex_enterprise::clock::SystemClock`

## Para qué sirve

Puerto de `cortex.autopilot.lifecycle`: tipos request/result de los flujos del servicio. La orquestación real queda tras el motor de sesiones.

## Relaciones

### Recibe de

- `use crate::policies::AutopilotMode`
- Contexto de crate `cortex-autopilot`: cortex-app, cortex-enterprise, cortex-workspace, cortex-mcp

### Envía a

- Crate `cortex-autopilot` envía hacia: cortex-cli autopilot, cortex-mcp handlers

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-autopilot/src/lifecycle.rs`.
