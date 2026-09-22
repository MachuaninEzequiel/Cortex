# rust/crates/cortex-doctor/src/checks.rs

## Qué tiene adentro

Tipos de salida del doctor — espejo de `DoctorCheck`/`DoctorReport`.
Archivo de 49 líneas.
Símbolos públicos observados:
- `pub type DoctorSeverity = &'static str`
- `pub struct DoctorCheck`
- `pub struct DoctorReport`

## Para qué sirve

Tipos de salida del doctor — espejo de `DoctorCheck`/`DoctorReport`.

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-doctor`: cortex-app, cortex-config, cortex-autopilot, cortex-enterprise, cortex-workspace

### Envía a

- Crate `cortex-doctor` envía hacia: cortex-cli doctor, cortex-brain tools cortex.health

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-doctor/src/checks.rs`.
