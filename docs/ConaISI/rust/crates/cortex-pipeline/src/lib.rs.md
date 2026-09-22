# rust/crates/cortex-pipeline/src/lib.rs

## Qué tiene adentro

Puerto de `cortex.pipeline` (P12B-6): tipos, contexto, trait de stage, orquestador con gates, stages subprocess y generador GitHub Actions.
Archivo de 13 líneas.
Símbolos públicos observados:
- `pub mod domain`
- `pub mod orchestrator`
- `pub mod runners`
- `pub mod stages`
- `pub use domain::`
- `pub use orchestrator::`

## Para qué sirve

Puerto de `cortex.pipeline` (P12B-6): tipos, contexto, trait de stage, orquestador con gates, stages subprocess y generador GitHub Actions.

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-pipeline`: cortex-enterprise, cortex-app, cortex-services, cortex-workspace

### Envía a

- Crate `cortex-pipeline` envía hacia: StageResult/PipelineReport, GitHub Actions YAML

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-pipeline/src/lib.rs`.
