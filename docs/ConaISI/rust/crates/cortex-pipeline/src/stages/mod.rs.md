# rust/crates/cortex-pipeline/src/stages/mod.rs

## Qué tiene adentro

Stages nativos. Test/Lint/Security ejecutan comandos locales (subprocess con timeout por polling, como runtime_context); Documentation queda en stub contractual hasta motor de memory nativo.
Archivo de 28 líneas.
Símbolos públicos observados:
- `pub mod documentation`
- `pub mod lint`
- `pub mod security`
- `pub mod test`
- `pub fn run_command(cmd: &str, _timeout_s: u64) -> (i32, String)`

## Para qué sirve

Stages nativos. Test/Lint/Security ejecutan comandos locales (subprocess con timeout por polling, como runtime_context); Documentation queda en stub contractual hasta motor de memory nativo.

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-pipeline`: cortex-enterprise, cortex-app, cortex-services, cortex-workspace

### Envía a

- Crate `cortex-pipeline` envía hacia: StageResult/PipelineReport, GitHub Actions YAML

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-pipeline/src/stages/mod.rs`.
