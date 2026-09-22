# rust/crates/cortex-autopilot/src/service.rs

## Qué tiene adentro

Puerto de `cortex.autopilot.service` — `AutopilotService` (Cierre T3).  Orquestador delgado que cablea: - [`cortex_app::session::service::SessionService`] NATIVO para el ciclo de vida (el `SessionRecord` es el estado canónico), - la capa de decisión P12B-5 ([`crate::policies`] + [`crate::detectors`]) para warnings/bloqueos en los hooks y el dry-run *preflight*, - un backend opcional [`DocumenterFinalize`] para `finish(auto=True)` (equivalente del `memory_factory` perezoso del oráculo; sin él el cierre automático devuelve fallo EXPLÍCITO con el mensaje exacto).  El servicio NO abre sesiones: `start` ADOPTA la sesión activa
Archivo de 597 líneas.
Símbolos públicos observados:
- `pub enum ServiceError`
- `pub struct FinalizeOutcome`
- `pub trait DocumenterFinalize: Send`
- `pub struct StartOutcome`
- `pub struct PreflightOutcome`
- `pub struct CheckpointOutcome`
- `pub struct FinishOutcome`
- `pub struct StatusOutcome`
- `pub struct AutopilotService`
- `pub const VALID_SOURCES: &[&str] = &[`
- `pub(crate) fn py_repr(s: &str) -> String`
- `pub fn to_decision_record(r: &SessionRecord) -> decision::SessionRecord`

## Para qué sirve

Puerto de `cortex.autopilot.service` — `AutopilotService` (Cierre T3).  Orquestador delgado que cablea: - [`cortex_app::session::service::SessionService`] NATIVO para el ciclo de vida (el `SessionRecord` es el estado canónico), - la capa de decisión P12B-5 ([`crate::policies`] + [`crate::detectors`]) para warnings/bloqueos en los hooks y el dry-run *preflight*, - un backend opcional [`DocumenterFinalize`] para `finish(auto=True)` (equivalente del `memory_factory` perezoso del oráculo; sin él el cierre automático devuelve fallo EXPLÍCITO con el mensaje exacto).  El servicio NO abre sesiones: `start` ADOPTA la sesión activa

## Relaciones

### Recibe de

- `use cortex_app::session::service::SessionService`
- `use cortex_app::session::{`
- `use crate::detectors::{default_detectors, resolve_detectors, AutopilotDetector}`
- `use crate::models::DetectionRequest`
- `use crate::policies::{AutopilotMode, AutopilotPolicy, EnforcementSeverity, PolicyEnforcer}`
- `use crate::session_models as decision`
- Contexto de crate `cortex-autopilot`: cortex-app, cortex-enterprise, cortex-workspace, cortex-mcp

### Envía a

- Crate `cortex-autopilot` envía hacia: cortex-cli autopilot, cortex-mcp handlers

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-autopilot/src/service.rs`.
