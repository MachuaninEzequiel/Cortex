# rust/crates/cortex-enterprise/tests/reporting.rs

## Qué tiene adentro

Archivo de 186 líneas.
Snapshot estático con checks reales estilo doctor Python.
Tests: `all_scope_calls_doctor_once_and_reports_both_vaults`, `default_backend_fails_explicitly`, `local_scope_uses_project_doctor_and_single_source`, `promotion_disabled_reports_enabled_false_with_require_review`

## Para qué sirve

Snapshot estático con checks reales estilo doctor Python.

## Relaciones

### Recibe de

- `use cortex_enterprise::clock::FixedClock`
- `use cortex_enterprise::config::{build_enterprise_org_config, write_enterprise_config}`
- `use cortex_enterprise::models::OrgProfile`
- `use cortex_enterprise::reporting::{`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-enterprise/tests/reporting.rs`. 186 líneas.
