# rust/crates/cortex-actions/src/registry.rs

## Qué tiene adentro

Puerto de `cortex/action_engine/registry.py` — catálogo de acciones registradas por id (sin duplicados). El orden de inserción es observable (desempate estable del scheduler ⇒ debe replicarse con Vec).
Archivo de 91 líneas.
Símbolos públicos observados:
- `pub struct Registry`
Tests en el mismo archivo: `duplicados_rechazados`, `orden_de_insercion_preservado`

## Para qué sirve

Puerto de `cortex/action_engine/registry.py` — catálogo de acciones registradas por id (sin duplicados). El orden de inserción es observable (desempate estable del scheduler ⇒ debe replicarse con Vec).

## Relaciones

### Recibe de

- `use crate::models::Action`
- `use crate::models::{ActionResult, Categoria}`
- Contexto de crate `cortex-actions`: cortex-app, cortex-enterprise, cortex-setup

### Envía a

- Crate `cortex-actions` envía hacia: cortex-cli next, cortex-companion, cortex-tui, .cortex/action_log.jsonl

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-actions/src/registry.rs`.
