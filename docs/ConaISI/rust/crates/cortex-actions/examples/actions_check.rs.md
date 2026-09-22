# rust/crates/cortex-actions/examples/actions_check.rs

## Qué tiene adentro

Archivo de 345 líneas.
Verificador de paridad P6 — cortex-actions vs oráculo Python (`cortex next`).  Uso: actions_check <fixtures_dir> <golden_dir>  Para cada escenario recalcula —con la MISMA semántica del CLI Python— las cuatro salidas gateadas (next_stats.json, next_json.json, next_why_not.json, next_texto.txt), aplica la misma normalización ({{ROOT}}, {{MS}}) y compara byte-a-byte contra los goldens capturados por bench/parity/actions_golden_p6.py.  La serialización es manual (emitter propio con orden de claves de inserción) porque `next` en Python emite dicts ordenados por inserción y

## Para qué sirve

Verificador de paridad P6 — cortex-actions vs oráculo Python (`cortex next`).  Uso: actions_check <fixtures_dir> <golden_dir>  Para cada escenario recalcula —con la MISMA semántica del CLI Python— las cuatro salidas gateadas (next_stats.json, next_json.json, next_why_not.json, next_texto.txt), aplica la misma normalización ({{ROOT}}, {{MS}}) y compara byte-a-byte contra los goldens capturados por bench/parity/actions_golden_p6.py.  La serialización es manual (emitter propio con orden de claves de inserción) porque `next` en Python emite dicts ordenados por inserción y

## Relaciones

### Recibe de

- `use cortex_actions::catalog::build_default_registry`
- `use cortex_actions::context::ActionContext`
- `use cortex_actions::metrics::calcular_metricas`
- `use cortex_actions::models::{redondear, Action}`
- `use cortex_actions::scheduler::Scheduler`
- `use cortex_actions::store::{ActionLog, PreferencesStore}`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-actions/examples/actions_check.rs`. 345 líneas.
