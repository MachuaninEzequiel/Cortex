# rust/crates/cortex-autopilot/tests/decision_layer.rs

## Qué tiene adentro

Archivo de 242 líneas.
Tests: `detectors_match_python_results`, `resolve_detectors_rules_match_python`, `config_defaults_and_parse_error_match_python`, `policy_defaults_from_config_and_validation`, `enforcer_hooks_match_python_texts`

## Para qué sirve

Archivo de soporte de `rust/crates/cortex-autopilot/tests/decision_layer.rs` (test, example, manifiesto o config).

## Relaciones

### Recibe de

- `use cortex_autopilot::config::load_autopilot_config`
- `use cortex_autopilot::detectors::AutopilotDetector`
- `use cortex_autopilot::detectors::{`
- `use cortex_autopilot::models::DetectionRequest`
- `use cortex_autopilot::policies::{`
- `use cortex_autopilot::session_models::{Checkpoint, CheckpointSource, SessionRecord}`
- `use cortex_workspace::WorkspaceLayout`
- `use cortex_enterprise::clock::{Clock, SystemClock}`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-autopilot/tests/decision_layer.rs`. 242 líneas.
