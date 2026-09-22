# rust/crates/cortex-doctor/src/native.rs

## Qué tiene adentro

Adapter `NativeDoctorBackend`: cierra el seam enterprise→doctor dejado en P12B-3. Implementa `cortex_enterprise::reporting::DoctorBackend` convirtiendo el reporte nativo a las vistas neutrales.
Archivo de 97 líneas.
Símbolos públicos observados:
- `pub(crate) fn python_resolve(path: &Path) -> PathBuf`
- `pub struct NativeDoctorBackend`

## Para qué sirve

Adapter `NativeDoctorBackend`: cierra el seam enterprise→doctor dejado en P12B-3. Implementa `cortex_enterprise::reporting::DoctorBackend` convirtiendo el reporte nativo a las vistas neutrales.

## Relaciones

### Recibe de

- `use crate::checks::DoctorCheck`
- `use crate::doctor::run_doctor`
- `use cortex_enterprise::error::EnterpriseError`
- `use cortex_enterprise::reporting::DoctorScope`
- `use cortex_enterprise::reporting::{DoctorBackend, DoctorCheckView, DoctorReportView}`
- Contexto de crate `cortex-doctor`: cortex-app, cortex-config, cortex-autopilot, cortex-enterprise, cortex-workspace

### Envía a

- Crate `cortex-doctor` envía hacia: cortex-cli doctor, cortex-brain tools cortex.health

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-doctor/src/native.rs`.
