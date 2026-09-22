# rust/crates/cortex-autopilot/src/detectors/mod.rs

## Qué tiene adentro

Puerto de `cortex.autopilot.detectors`: protocolo, resolución §7.1.2 y los 8 detectores built-in.
Archivo de 112 líneas.
Símbolos públicos observados:
- `pub mod ambiguous`
- `pub mod default`
- `pub use ambiguous::AmbiguousRequestDetector`
- `pub use default::`
- `pub trait AutopilotDetector`
- `pub fn default_detectors() -> Vec<Box<dyn AutopilotDetector + Send>>`
- `pub fn resolve_detectors(`

## Para qué sirve

Puerto de `cortex.autopilot.detectors`: protocolo, resolución §7.1.2 y los 8 detectores built-in.

## Relaciones

### Recibe de

- `use cortex_enterprise::error::EnterpriseError`
- `use crate::models::{DetectionRequest, DetectionResult}`
- Contexto de crate `cortex-autopilot`: cortex-app, cortex-enterprise, cortex-workspace, cortex-mcp

### Envía a

- Crate `cortex-autopilot` envía hacia: cortex-cli autopilot, cortex-mcp handlers

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-autopilot/src/detectors/mod.rs`.
