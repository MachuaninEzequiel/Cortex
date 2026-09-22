# rust/crates/cortex-enterprise/tests/retrieval.rs

## Qué tiene adentro

Archivo de 322 líneas.
Tests: `all_scope_deduplicates_same_semantic_path_preferring_enterprise`, `local_scope_annotates_only_local_and_truncates`, `project_id_filter_keeps_matching_origins_only`, `enterprise_scope_without_sources_fails_with_python_message`, `enterprise_weight_boosts_rank_and_ties_are_stable`, `clock_is_unused_but_available_for_future_native_glue`

## Para qué sirve

Archivo de soporte de `rust/crates/cortex-enterprise/tests/retrieval.rs` (test, example, manifiesto o config).

## Relaciones

### Recibe de

- `use cortex_enterprise::clock::FixedClock`
- `use cortex_enterprise::config::build_enterprise_org_config`
- `use cortex_enterprise::error::EnterpriseError`
- `use cortex_enterprise::retrieval::{`
- `use cortex_enterprise::sources::{`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-enterprise/tests/retrieval.rs`. 322 líneas.
