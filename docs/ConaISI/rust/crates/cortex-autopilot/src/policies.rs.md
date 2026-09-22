# rust/crates/cortex-autopilot/src/policies.rs

## Qué tiene adentro

Puerto de `cortex.autopilot.policies`: modo, policy inmutable y enforcer de lifecycle hooks. Todos los mensajes contractuales se replican.
Archivo de 380 líneas.
Símbolos públicos observados:
- `pub enum AutopilotMode`
- `pub enum EnforcementSeverity`
- `pub struct EnforcementResult`
- `pub const DEFAULT_BUDGET_PROFILE: &str = "fast_code"`
- `pub const KNOWN_BUDGET_PROFILES: &[&str] = &[`
- `pub struct AutopilotPolicy`
- `pub struct PolicyEnforcer`
- `pub(crate) fn py_list_repr(items: &[String]) -> String`

## Para qué sirve

Puerto de `cortex.autopilot.policies`: modo, policy inmutable y enforcer de lifecycle hooks. Todos los mensajes contractuales se replican.

## Relaciones

### Recibe de

- `use cortex_enterprise::clock::Clock`
- `use cortex_enterprise::error::EnterpriseError`
- `use crate::config::AutopilotConfig`
- `use crate::session_models::{Checkpoint, SessionRecord, SessionStatus}`
- Contexto de crate `cortex-autopilot`: cortex-app, cortex-enterprise, cortex-workspace, cortex-mcp

### Envía a

- Crate `cortex-autopilot` envía hacia: cortex-cli autopilot, cortex-mcp handlers

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-autopilot/src/policies.rs`.
