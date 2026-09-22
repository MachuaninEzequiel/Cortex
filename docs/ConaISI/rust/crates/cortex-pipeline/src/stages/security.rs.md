# rust/crates/cortex-pipeline/src/stages/security.rs

## Qué tiene adentro

Puerto de `stages/security.py`: auditoría de dependencias.
Archivo de 76 líneas.
Símbolos públicos observados:
- `pub struct SecurityStage`

## Para qué sirve

Puerto de `stages/security.py`: auditoría de dependencias.

## Relaciones

### Recibe de

- `use crate::domain::context::PipelineContext`
- `use crate::domain::types::{StageResult, StageStatus, StageType}`
- `use crate::stages::run_command`
- Contexto de crate `cortex-pipeline`: cortex-enterprise, cortex-app, cortex-services, cortex-workspace

### Envía a

- Crate `cortex-pipeline` envía hacia: StageResult/PipelineReport, GitHub Actions YAML

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-pipeline/src/stages/security.rs`.
