# rust/crates/cortex-actions/src/learning.rs

## Qué tiene adentro

Puerto de `cortex/action_engine/learning.py` — paso APRENDER v0 (plan §3.6). Bucle mínimo: cada decisión (accept/skip/never) se persiste en `.cortex/actions.yaml` y ajusta el score futuro vía `PreferencesStore::penalizacion_skips`.
Archivo de 60 líneas.
Símbolos públicos observados:
- `pub struct Learner`
Tests en el mismo archivo: `bucle_minimo_aprender`

## Para qué sirve

Puerto de `cortex/action_engine/learning.py` — paso APRENDER v0 (plan §3.6). Bucle mínimo: cada decisión (accept/skip/never) se persiste en `.cortex/actions.yaml` y ajusta el score futuro vía `PreferencesStore::penalizacion_skips`.

## Relaciones

### Recibe de

- `use crate::store::PreferencesStore`
- Contexto de crate `cortex-actions`: cortex-app, cortex-enterprise, cortex-setup

### Envía a

- Crate `cortex-actions` envía hacia: cortex-cli next, cortex-companion, cortex-tui, .cortex/action_log.jsonl

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-actions/src/learning.rs`.
