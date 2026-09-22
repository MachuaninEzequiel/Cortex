# rust/crates/cortex-enterprise/src/lib.rs

## Qué tiene adentro

Puerto de `cortex/enterprise/` (P12B-3): modelos org, config YAML byte-parity, gobernanza multi-tenant, promoción de conocimiento, retención, retrieval multi-scope y reporting con backend doctor inyectable.
Archivo de 18 líneas.
Símbolos públicos observados:
- `pub mod clock`
- `pub mod config`
- `pub mod error`
- `pub mod frontmatter`
- `pub mod governance`
- `pub mod knowledge_promotion`
- `pub mod maintenance`
- `pub mod models`
- `pub mod promotion_doctype`
- `pub mod promotion_models`
- `pub mod reporting`
- `pub mod retrieval`
- `pub mod review_knowledge`
- `pub mod sources`

## Para qué sirve

Puerto de `cortex/enterprise/` (P12B-3): modelos org, config YAML byte-parity, gobernanza multi-tenant, promoción de conocimiento, retención, retrieval multi-scope y reporting con backend doctor inyectable.

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-enterprise`: cortex-app, cortex-setup, cortex-workspace

### Envía a

- Crate `cortex-enterprise` envía hacia: cortex-cli enterprise, cortex-doctor, cortex-actions knowledge.promote, cortex-brain-app org_memory

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-enterprise/src/lib.rs`.
