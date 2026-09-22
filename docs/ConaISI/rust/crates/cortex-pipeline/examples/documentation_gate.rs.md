# rust/crates/cortex-pipeline/examples/documentation_gate.rs

## Qué tiene adentro

Archivo de 105 líneas.
Checker del segmento `### DOCUMENTATION` del gate `pipeline_golden_p12b.py` (T4): corre el `DocumentationStage` REAL sobre un fixture (vault + sesión gitless + spec) y emite el `StageResult` CONGELADO — timestamp fijo y `duration_ms` 0 — como una línea JSON que el gate normaliza ({{ROOT}}, {{ID}}) y congela en el golden.  Uso: documentation_gate <root> <fixed_ts> <block:0|1> <changed_csv> [pr_ctx:0|1]  `root` debe contener (layout v2): `.cortex/workspace.yaml`, `.cortex/vault/` (con la spec referenciada por la sesión) y `.cortex/sessions/*.yaml` (sesión gitless con `start_branch` == branch del PR). Determinista: el

## Para qué sirve

Checker del segmento `### DOCUMENTATION` del gate `pipeline_golden_p12b.py` (T4): corre el `DocumentationStage` REAL sobre un fixture (vault + sesión gitless + spec) y emite el `StageResult` CONGELADO — timestamp fijo y `duration_ms` 0 — como una línea JSON que el gate normaliza ({{ROOT}}, {{ID}}) y congela en el golden.  Uso: documentation_gate <root> <fixed_ts> <block:0|1> <changed_csv> [pr_ctx:0|1]  `root` debe contener (layout v2): `.cortex/workspace.yaml`, `.cortex/vault/` (con la spec referenciada por la sesión) y `.cortex/sessions/*.yaml` (sesión gitless con `start_branch` == branch del PR). Determinista: el

## Relaciones

### Recibe de

- `use cortex_app::pr::PRContext`
- `use cortex_app::session::service::SessionService`
- `use cortex_app::session::SessionStorage`
- `use cortex_pipeline::domain::context::PipelineContext`
- `use cortex_pipeline::domain::types::{StageResult, StageStatus}`
- `use cortex_pipeline::orchestrator::PipelineStage`
- `use cortex_pipeline::stages::documentation::DocumentationStage`
- `use cortex_workspace::WorkspaceLayout`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-pipeline/examples/documentation_gate.rs`. 105 líneas.
