# rust/crates/cortex-doctor/tests/doctor_core.rs

## Qué tiene adentro

Archivo de 213 líneas.
Tests: `core_portable_checks_order_and_details_match_python`, `missing_root_returns_only_two_checks`, `new_layout_uses_new_gitignore_patterns_and_workspace_yaml_info`, `enterprise_scope_requires_org_yaml_and_validates_full_block`, `native_backend_implements_reporting_seam`, `pm_documenter_module_ok_si_load_spec_anda`

## Para qué sirve

Archivo de soporte de `rust/crates/cortex-doctor/tests/doctor_core.rs` (test, example, manifiesto o config).

## Relaciones

### Recibe de

- `use cortex_doctor::doctor::{run_doctor, DoctorScope}`
- `use cortex_enterprise::config::{build_enterprise_org_config, write_enterprise_config}`
- `use cortex_doctor::native::NativeDoctorBackend`
- `use cortex_enterprise::reporting::{DoctorBackend, ReportingScope}`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-doctor/tests/doctor_core.rs`. 213 líneas.
