# rust/crates/cortex-pipeline/tests/pipeline_core.rs

## Qué tiene adentro

Archivo de 91 líneas.
Tests: `all_pass_flow`, `blocking_failure_skips_remaining`, `non_blocking_failure_continues`, `markdown_table_renders`

## Para qué sirve

Archivo de soporte de `rust/crates/cortex-pipeline/tests/pipeline_core.rs` (test, example, manifiesto o config).

## Relaciones

### Recibe de

- `use cortex_pipeline::{PipelineContext, PipelineOrchestrator, StageResult, StageStatus, StageType}`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-pipeline/tests/pipeline_core.rs`. 91 líneas.
