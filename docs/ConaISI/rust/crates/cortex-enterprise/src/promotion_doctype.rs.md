# rust/crates/cortex-enterprise/src/promotion_doctype.rs

## Qué tiene adentro

Puerto de `cortex.enterprise.promotion_doctype` (Fase 10): promoción DocType-aware con modos `as-is` / `summarize` / `review-required`, frontmatter enterprise con audit trail, y cola de drafts.  La tabla canónica vive en `cortex_setup::routing::resolve_route` (promotable/enterprise_subfolder). Los campos `promotion_mode` y `requires_review_before_publish`, aún ausentes del RouteSpec nativo, se espejan localmente 1:1 desde `cortex/documentation/routing.py`.
Archivo de 665 líneas.
Símbolos públicos observados:
- `pub struct PromotionResult`
- `pub struct PromoteArgs<'a>`
- `pub fn promote_note_doctype_aware(`
- `pub fn mark_as_accepted(`
- `pub fn mark_as_rejected(`
- `pub struct PendingDraft`
- `pub fn list_pending_drafts(vault_root: &Path, doc_types: Option<&[String]>) -> Vec<PendingDraft>`

## Para qué sirve

Puerto de `cortex.enterprise.promotion_doctype` (Fase 10): promoción DocType-aware con modos `as-is` / `summarize` / `review-required`, frontmatter enterprise con audit trail, y cola de drafts.  La tabla canónica vive en `cortex_setup::routing::resolve_route` (promotable/enterprise_subfolder). Los campos `promotion_mode` y `requires_review_before_publish`, aún ausentes del RouteSpec nativo, se espejan localmente 1:1 desde `cortex/documentation/routing.py`.

## Relaciones

### Recibe de

- `use cortex_setup::doc_type::DocType`
- `use cortex_setup::routing::resolve_route`
- `use cortex_setup::yaml as pyyaml`
- `use crate::clock::{isoformat_full, Clock}`
- `use crate::error::EnterpriseError`
- `use crate::frontmatter::{split_frontmatter, yaml_value_to_node}`
- `use crate::governance`
- `use crate::models::EnterpriseOrgConfig`
- Contexto de crate `cortex-enterprise`: cortex-app, cortex-setup, cortex-workspace

### Envía a

- Crate `cortex-enterprise` envía hacia: cortex-cli enterprise, cortex-doctor, cortex-actions knowledge.promote, cortex-brain-app org_memory

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-enterprise/src/promotion_doctype.rs`.
