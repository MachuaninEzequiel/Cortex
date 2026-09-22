# rust/crates/cortex-enterprise/src/maintenance.rs

## Qué tiene adentro

Puerto de `cortex.enterprise.maintenance`: escaneo de retención y archivo a `<vault>/_archived/` preservando estructura.
Archivo de 197 líneas.
Símbolos públicos observados:
- `pub struct RetentionViolation`
- `pub fn scan_retention_violations(`
- `pub fn archive_violations(`

## Para qué sirve

Puerto de `cortex.enterprise.maintenance`: escaneo de retención y archivo a `<vault>/_archived/` preservando estructura.

## Relaciones

### Recibe de

- `use crate::models::{EnterpriseOrgConfig, RetentionPolicy}`
- Contexto de crate `cortex-enterprise`: cortex-app, cortex-setup, cortex-workspace

### Envía a

- Crate `cortex-enterprise` envía hacia: cortex-cli enterprise, cortex-doctor, cortex-actions knowledge.promote, cortex-brain-app org_memory

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-enterprise/src/maintenance.rs`.
