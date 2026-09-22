# rust/crates/cortex-actions/src/scheduler.rs

## Qué tiene adentro

Puerto de `cortex/action_engine/scheduler.py` (Obra 05 Fase B, plan §3.4).  Evalúa precondiciones + preferencias, calcula score (impacto × frescura − costo) y devuelve máximo `max_visible` propuestas.
Archivo de 243 líneas.
Símbolos públicos observados:
- `pub const MAX_VISIBLE_DEFAULT: usize = 5`
- `pub struct Scheduler<'a>`
Tests en el mismo archivo: `precondicion_falla_no_ofrece`, `nunca_mas_suprime`, `skips_bajan_score_y_accepts_compensan`, `max_visible`, `orden_estable_por_score`

## Para qué sirve

Puerto de `cortex/action_engine/scheduler.py` (Obra 05 Fase B, plan §3.4).  Evalúa precondiciones + preferencias, calcula score (impacto × frescura − costo) y devuelve máximo `max_visible` propuestas.

## Relaciones

### Recibe de

- `use crate::models::{costo_penalizacion, impacto_base, redondear, Action, ProposedAction}`
- `use crate::registry::Registry`
- `use crate::signals::multiplicador_categoria`
- `use crate::signals::MemorySignals`
- `use crate::store::PreferencesStore`
- `use crate::models::{ActionResult, Categoria, Check, Costo}`
- Contexto de crate `cortex-actions`: cortex-app, cortex-enterprise, cortex-setup

### Envía a

- Crate `cortex-actions` envía hacia: cortex-cli next, cortex-companion, cortex-tui, .cortex/action_log.jsonl

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-actions/src/scheduler.rs`.
