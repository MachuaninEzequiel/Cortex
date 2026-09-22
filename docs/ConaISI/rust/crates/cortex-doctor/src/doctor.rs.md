# rust/crates/cortex-doctor/src/doctor.rs

## Qué tiene adentro

Puerto de `cortex.doctor` (P12B-4): checks nativos completos para todo lo filesystem/config/git/gitignore/vault/enterprise, y stubs contractuales (patrón P6/P9) para backends Python aún no porteños.  Contrato de stubs (congelado; el oráculo normaliza por nombre): `ok=false · severity=warn|fail según check · detail="backend no nativo aún (<módulo python>)"`.
Archivo de 841 líneas.
Símbolos públicos observados:
- `pub enum DoctorScope`
- `pub type EnterpriseErrorLike = cortex_enterprise::error::EnterpriseError`
- `pub fn run_doctor(`

## Para qué sirve

Puerto de `cortex.doctor` (P12B-4): checks nativos completos para todo lo filesystem/config/git/gitignore/vault/enterprise, y stubs contractuales (patrón P6/P9) para backends Python aún no porteños.  Contrato de stubs (congelado; el oráculo normaliza por nombre): `ok=false · severity=warn|fail según check · detail="backend no nativo aún (<módulo python>)"`.

## Relaciones

### Recibe de

- `use cortex_app::doc_validator::DocValidator`
- `use cortex_enterprise::config::{describe_enterprise_topology, load_enterprise_config}`
- `use cortex_workspace::runtime_context::{`
- `use cortex_workspace::{`
- `use crate::checks::{DoctorCheck, DoctorReport}`
- `use cortex_autopilot::config::load_autopilot_config`
- `use cortex_app::session::{CheckpointSource, SessionStorage}`
- `use cortex_enterprise::models::RetrievalScope`
- Contexto de crate `cortex-doctor`: cortex-app, cortex-config, cortex-autopilot, cortex-enterprise, cortex-workspace

### Envía a

- Crate `cortex-doctor` envía hacia: cortex-cli doctor, cortex-brain tools cortex.health

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-doctor/src/doctor.rs`.
