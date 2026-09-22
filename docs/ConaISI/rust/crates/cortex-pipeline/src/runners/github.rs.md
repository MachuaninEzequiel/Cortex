# rust/crates/cortex-pipeline/src/runners/github.rs

## Qué tiene adentro

Puerto de `runners/github.py`: generador puro de workflow YAML. Los f-strings con `{{ }}` de Python se vuelven literales `{ }`.
Archivo de 279 líneas.
Símbolos públicos observados:
- `pub struct GitHubActionsRunner`

## Para qué sirve

Puerto de `runners/github.py`: generador puro de workflow YAML. Los f-strings con `{{ }}` de Python se vuelven literales `{ }`.

## Relaciones

### Recibe de

- `use crate::domain::types::StageType::*`
- Contexto de crate `cortex-pipeline`: cortex-enterprise, cortex-app, cortex-services, cortex-workspace

### Envía a

- Crate `cortex-pipeline` envía hacia: StageResult/PipelineReport, GitHub Actions YAML

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-pipeline/src/runners/github.rs`.
