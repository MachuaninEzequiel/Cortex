# rust/crates/cortex-doctor/examples/doctor_check.rs

## Qué tiene adentro

Archivo de 227 líneas.
Gate P12B-4: reproduce `golden_doctor.txt` byte-a-byte.  Uso: cargo run -p cortex-doctor --example doctor_check -- \ ../bench/parity/.p12b-doctor Serializa un reporte al formato del golden: una línea JSON por check + SUMMARY final con bools estilo Python.

## Para qué sirve

Gate P12B-4: reproduce `golden_doctor.txt` byte-a-byte.  Uso: cargo run -p cortex-doctor --example doctor_check -- \ ../bench/parity/.p12b-doctor Serializa un reporte al formato del golden: una línea JSON por check + SUMMARY final con bools estilo Python.

## Relaciones

### Recibe de

- `use cortex_doctor::checks::DoctorReport`
- `use cortex_doctor::doctor::{run_doctor, DoctorScope}`
- `use cortex_enterprise::config::{build_enterprise_org_config, write_enterprise_config}`
- `use cortex_app::session::service::SessionService`
- `use cortex_app::session::SessionStorage`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-doctor/examples/doctor_check.rs`. 227 líneas.
