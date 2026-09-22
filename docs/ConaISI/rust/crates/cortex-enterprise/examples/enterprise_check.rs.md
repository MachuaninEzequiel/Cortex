# rust/crates/cortex-enterprise/examples/enterprise_check.rs

## Qué tiene adentro

Archivo de 815 líneas.
Gate de paridad P12B-3: reproduce `golden_enterprise.txt` byte-a-byte usando las APIs nativas de cortex-enterprise + fakes deterministas.  Uso: cargo run -p cortex-enterprise --example enterprise_check -- \ ../bench/parity/.p12b-enterprise  Normalización idéntica a `norm()` del oráculo: root → {{ROOT}} y todo timestamp ISO → {{TS}}.

## Para qué sirve

Gate de paridad P12B-3: reproduce `golden_enterprise.txt` byte-a-byte usando las APIs nativas de cortex-enterprise + fakes deterministas.  Uso: cargo run -p cortex-enterprise --example enterprise_check -- \ ../bench/parity/.p12b-enterprise  Normalización idéntica a `norm()` del oráculo: root → {{ROOT}} y todo timestamp ISO → {{TS}}.

## Relaciones

### Recibe de

- `use cortex_enterprise::clock::FixedClock`
- `use cortex_enterprise::config::{`
- `use cortex_enterprise::error::EnterpriseError`
- `use cortex_enterprise::knowledge_promotion::KnowledgePromotionService`
- `use cortex_enterprise::maintenance::{archive_violations, scan_retention_violations}`
- `use cortex_enterprise::models::OrgProfile`
- `use cortex_enterprise::models::{PromotableDocType, RetentionPolicy}`
- `use cortex_enterprise::promotion_doctype::{`
- `use cortex_enterprise::reporting::{`
- `use cortex_enterprise::governance as gov`
- `use cortex_enterprise::models::TeamConfig`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-enterprise/examples/enterprise_check.rs`. 815 líneas.
