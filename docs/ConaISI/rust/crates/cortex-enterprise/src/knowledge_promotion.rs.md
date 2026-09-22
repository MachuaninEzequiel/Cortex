# rust/crates/cortex-enterprise/src/knowledge_promotion.rs

## Qué tiene adentro

Puerto de `cortex.enterprise.knowledge_promotion`: descubrimiento de candidatos, review con records JSONL append-only y promoción idempotente.  Paridad clave: - `discover_candidates` recarga org.yaml del disco en cada llamada (igual que Python; ver ruling en ledger). - Los candidatos se recorren con `sorted(rglob("*.md"))` y los promovidos con fingerprint vigente NO reaparecen. - `review`/`apply` reproducen mensajes ValueError textuales.
Archivo de 578 líneas.
Símbolos públicos observados:
- `pub struct PromotionPaths`
- `pub struct PromotionRepository`
- `pub struct PromotionRulesEngine`
- `pub struct KnowledgePromotionService`

## Para qué sirve

Puerto de `cortex.enterprise.knowledge_promotion`: descubrimiento de candidatos, review con records JSONL append-only y promoción idempotente.  Paridad clave: - `discover_candidates` recarga org.yaml del disco en cada llamada (igual que Python; ver ruling en ledger). - Los candidatos se recorren con `sorted(rglob("*.md"))` y los promovidos con fingerprint vigente NO reaparecen. - `review`/`apply` reproducen mensajes ValueError textuales.

## Relaciones

### Recibe de

- `use cortex_app::doc_validator::{DocValidator, Severity}`
- `use cortex_workspace::{runtime_context::slugify, WorkspaceLayout}`
- `use crate::clock::{isoformat_seconds, Clock}`
- `use crate::config::load_enterprise_config`
- `use crate::error::EnterpriseError`
- `use crate::frontmatter::{`
- `use crate::governance`
- `use crate::models::EnterpriseOrgConfig`
- `use crate::promotion_models::{`
- Contexto de crate `cortex-enterprise`: cortex-app, cortex-setup, cortex-workspace

### Envía a

- Crate `cortex-enterprise` envía hacia: cortex-cli enterprise, cortex-doctor, cortex-actions knowledge.promote, cortex-brain-app org_memory

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-enterprise/src/knowledge_promotion.rs`.
