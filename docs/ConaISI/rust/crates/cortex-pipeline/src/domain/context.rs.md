# rust/crates/cortex-pipeline/src/domain/context.rs

## Qué tiene adentro

`PipelineContext` — contexto compartido entre stages.
Archivo de 36 líneas.
Símbolos públicos observados:
- `pub struct PipelineContext`

## Para qué sirve

`PipelineContext` — contexto compartido entre stages.

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-pipeline`: cortex-enterprise, cortex-app, cortex-services, cortex-workspace

### Envía a

- Crate `cortex-pipeline` envía hacia: StageResult/PipelineReport, GitHub Actions YAML

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-pipeline/src/domain/context.rs`.
