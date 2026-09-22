# rust/crates/cortex-autopilot/src/lib.rs

## Qué tiene adentro

Puerto de `cortex.autopilot` — Cierre Obra 07 T3.  - Capa de decisión (P12B-5): config, models, session-models mínimos, detectors, policies y lifecycle. - [`service`] (T3): orquestación sobre el SessionService NATIVO (`cortex-app::session`) — start/preflight/checkpoint/finish/status. El cierre vía documenter (`finish(auto=True)`) requiere un backend [`service::DocumenterFinalize`] inyectado; sin él ⇒ fallo explícito con el mensaje exacto del oráculo (patrón P6/P9).
Archivo de 18 líneas.
Símbolos públicos observados:
- `pub mod config`
- `pub mod detectors`
- `pub mod errors`
- `pub mod lifecycle`
- `pub mod models`
- `pub mod policies`
- `pub mod service`
- `pub mod session_models`

## Para qué sirve

Puerto de `cortex.autopilot` — Cierre Obra 07 T3.  - Capa de decisión (P12B-5): config, models, session-models mínimos, detectors, policies y lifecycle. - [`service`] (T3): orquestación sobre el SessionService NATIVO (`cortex-app::session`) — start/preflight/checkpoint/finish/status. El cierre vía documenter (`finish(auto=True)`) requiere un backend [`service::DocumenterFinalize`] inyectado; sin él ⇒ fallo explícito con el mensaje exacto del oráculo (patrón P6/P9).

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-autopilot`: cortex-app, cortex-enterprise, cortex-workspace, cortex-mcp

### Envía a

- Crate `cortex-autopilot` envía hacia: cortex-cli autopilot, cortex-mcp handlers

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-autopilot/src/lib.rs`.
