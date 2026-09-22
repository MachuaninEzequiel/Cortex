# rust/crates/cortex-enterprise/src/governance.rs

## Qué tiene adentro

Puerto de `cortex.enterprise.governance`: permisos multi-tenant y visibilidad por clasificación. Módulo puro — no toca filesystem.  Paridad: primer match de equipo gana; `admin` es pseudo-equipo con acceso total; sin teams configurados ⇒ permisivo (back-compat); mensajes de denegación replican el repr de Python (`'alice'`, `None`).
Archivo de 137 líneas.
Símbolos públicos observados:
- `pub const ADMIN_TEAM: &str = "admin"`
- `pub fn user_team(actor: Option<&str>, org: &EnterpriseOrgConfig) -> Option<String>`
- `pub fn team_can_promote(team_id: Option<&str>, org: &EnterpriseOrgConfig) -> bool`
- `pub fn team_can_review(team_id: Option<&str>, org: &EnterpriseOrgConfig) -> bool`
- `pub fn classification_visible_to(`
- `pub fn allowed_classifications_for(`
- `pub fn assert_can_promote(`
- `pub fn assert_can_review(`

## Para qué sirve

Puerto de `cortex.enterprise.governance`: permisos multi-tenant y visibilidad por clasificación. Módulo puro — no toca filesystem.  Paridad: primer match de equipo gana; `admin` es pseudo-equipo con acceso total; sin teams configurados ⇒ permisivo (back-compat); mensajes de denegación replican el repr de Python (`'alice'`, `None`).

## Relaciones

### Recibe de

- `use crate::error::EnterpriseError`
- `use crate::models::{Classification, EnterpriseOrgConfig}`
- Contexto de crate `cortex-enterprise`: cortex-app, cortex-setup, cortex-workspace

### Envía a

- Crate `cortex-enterprise` envía hacia: cortex-cli enterprise, cortex-doctor, cortex-actions knowledge.promote, cortex-brain-app org_memory

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-enterprise/src/governance.rs`.
