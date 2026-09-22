# rust/crates/cortex-pipeline/src/orchestrator.rs

## Qué tiene adentro

`PipelineOrchestrator` — ejecuta stages en orden y aplica gates. Semántica exacta de Python: tras cada execute se registra el output; si un stage falla con block_on_failure y abort_early ⇒ los RESTANTES se marcan SKIPPED ("Skipped due to earlier gate failure.").
Archivo de 75 líneas.
Símbolos públicos observados:
- `pub trait PipelineStage`
- `pub type StageTypeAlias = crate::domain::types::StageType`
- `pub struct PipelineOrchestrator`

## Para qué sirve

`PipelineOrchestrator` — ejecuta stages en orden y aplica gates. Semántica exacta de Python: tras cada execute se registra el output; si un stage falla con block_on_failure y abort_early ⇒ los RESTANTES se marcan SKIPPED ("Skipped due to earlier gate failure.").

## Relaciones

### Recibe de

- `use crate::domain::context::PipelineContext`
- `use crate::domain::types::{PipelineReport, StageResult, StageStatus}`
- Contexto de crate `cortex-pipeline`: cortex-enterprise, cortex-app, cortex-services, cortex-workspace

### Envía a

- Crate `cortex-pipeline` envía hacia: StageResult/PipelineReport, GitHub Actions YAML

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-pipeline/src/orchestrator.rs`.
