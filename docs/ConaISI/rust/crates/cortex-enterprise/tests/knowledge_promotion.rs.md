# rust/crates/cortex-enterprise/tests/knowledge_promotion.rs

## Qué tiene adentro

Archivo de 230 líneas.
Tests: `reviewed_candidate_promotes_once_and_records_jsonl`, `jsonl_record_bytes_match_python_field_order`, `sessions_and_cortex_metadata_are_not_promotable_by_default`, `fingerprint_normalizes_crlf_and_strips_body_edges`, `invalid_jsonl_lines_are_skipped_silently`, `content_change_requires_new_review`, `validation_error_blocks_review`, `unknown_selector_reports_python_message`, `rules_engine_messages_match_python`

## Para qué sirve

Archivo de soporte de `rust/crates/cortex-enterprise/tests/knowledge_promotion.rs` (test, example, manifiesto o config).

## Relaciones

### Recibe de

- `use cortex_enterprise::clock::FixedClock`
- `use cortex_enterprise::config::build_enterprise_org_config`
- `use cortex_enterprise::knowledge_promotion::{`
- `use cortex_enterprise::models::{OrgProfile, PromotableDocType}`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-enterprise/tests/knowledge_promotion.rs`. 230 líneas.
