# rust/crates/cortex-enterprise/tests/doctype_review_maintenance.rs

## Qué tiene adentro

Archivo de 508 líneas.
Tests: `adr_as_is_preserves_body_and_appends_audit`, `session_summarizes_and_runbook_becomes_draft`, `promotion_error_precedence_and_gates_match_python`, `dry_run_writes_nothing_but_returns_result`, `approve_rejects_escape_from_enterprise_vault`, `accept_and_reject_mutations_match_python_semantics`, `pending_drafts_filter_sort_and_skip_rejected`, `retention_boundary_is_inclusive`, `retention_resolution_order_and_skips_match_python`, `archive_moves_preserving_relative_paths`

## Para qué sirve

Archivo de soporte de `rust/crates/cortex-enterprise/tests/doctype_review_maintenance.rs` (test, example, manifiesto o config).

## Relaciones

### Recibe de

- `use cortex_enterprise::clock::FixedClock`
- `use cortex_enterprise::config::build_enterprise_org_config`
- `use cortex_enterprise::maintenance::{archive_violations, scan_retention_violations}`
- `use cortex_enterprise::models::{OrgProfile, PromotableDocType, RetentionPolicy}`
- `use cortex_enterprise::promotion_doctype::{`
- `use cortex_enterprise::review_knowledge::{approve_output, reject_output}`
- `use cortex_workspace::WorkspaceLayout`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-enterprise/tests/doctype_review_maintenance.rs`. 508 líneas.
