# rust/crates/cortex-enterprise/src/reporting.rs

## Qué tiene adentro

Puerto de `cortex.enterprise.reporting`: reporte de memoria con doctor ejecutado UNA vez vía backend inyectado.  Seam enterprise→doctor (diseño aprobado P12B-3): enterprise define las vistas neutrales `DoctorReportView`/`DoctorCheckView` y el trait `DoctorBackend`. El default `UnavailableDoctorBackend` falla explícito; en P12B-4 cortex-doctor implementará `NativeDoctorBackend` y el ciclo queda doctor → enterprise, nunca inverso.
Archivo de 404 líneas.
Símbolos públicos observados:
- `pub enum DoctorScope`
- `pub struct DoctorCheckView`
- `pub struct DoctorReportView`
- `pub trait DoctorBackend: Send + Sync`
- `pub struct UnavailableDoctorBackend`
- `pub enum ReportingScope`
- `pub struct PromotionEventSummary`
- `pub struct PromotionReport`
- `pub struct MemorySourceReport`
- `pub struct MemoryReportPayload`
- `pub struct EnterpriseReportingService`

## Para qué sirve

Puerto de `cortex.enterprise.reporting`: reporte de memoria con doctor ejecutado UNA vez vía backend inyectado.  Seam enterprise→doctor (diseño aprobado P12B-3): enterprise define las vistas neutrales `DoctorReportView`/`DoctorCheckView` y el trait `DoctorBackend`. El default `UnavailableDoctorBackend` falla explícito; en P12B-4 cortex-doctor implementará `NativeDoctorBackend` y el ciclo queda doctor → enterprise, nunca inverso.

## Relaciones

### Recibe de

- `use crate::config::{discover_enterprise_config_path, load_enterprise_config}`
- `use crate::error::EnterpriseError`
- `use crate::knowledge_promotion::KnowledgePromotionService`
- `use crate::models::EnterpriseOrgConfig`
- `use cortex_workspace::WorkspaceLayout`
- Contexto de crate `cortex-enterprise`: cortex-app, cortex-setup, cortex-workspace

### Envía a

- Crate `cortex-enterprise` envía hacia: cortex-cli enterprise, cortex-doctor, cortex-actions knowledge.promote, cortex-brain-app org_memory

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-enterprise/src/reporting.rs`.
