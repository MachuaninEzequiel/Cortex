# rust/crates/cortex-enterprise/src/promotion_models.rs

## Qué tiene adentro

Puerto de `cortex.enterprise.promotion_models`: records append-only del ciclo de promoción. El orden de campos serde = orden de declaración Pydantic ⇒ `model_dump_json` byte-parity (compacto, unicode crudo).
Archivo de 131 líneas.
Símbolos públicos observados:
- `pub struct PromotionIssue`
- `pub struct PromotionCandidate`
- `pub struct PromotionDecision`
- `pub struct PromotionRecordEvent`
- `pub struct PromotionRecord`

## Para qué sirve

Puerto de `cortex.enterprise.promotion_models`: records append-only del ciclo de promoción. El orden de campos serde = orden de declaración Pydantic ⇒ `model_dump_json` byte-parity (compacto, unicode crudo).

## Relaciones

### Recibe de

- `use crate::clock::{default_now_string, Clock}`
- `use crate::error::EnterpriseError`
- Contexto de crate `cortex-enterprise`: cortex-app, cortex-setup, cortex-workspace

### Envía a

- Crate `cortex-enterprise` envía hacia: cortex-cli enterprise, cortex-doctor, cortex-actions knowledge.promote, cortex-brain-app org_memory

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-enterprise/src/promotion_models.rs`.
