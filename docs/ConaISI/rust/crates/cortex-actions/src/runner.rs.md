# rust/crates/cortex-actions/src/runner.rs

## Qué tiene adentro

Puerto de `cortex/action_engine/runner.py` (Obra 05 Fase B).  Ejecuta acciones aplicando las reglas duras del contrato: - dry-run nativo (pasa `dry_run=true` al run de la acción); - irreversible ⇒ exige `approved=true` explícito; - toda ejecución (incluidos dry-runs y fallos) queda en action_log.jsonl; - deshacer: `undo_last()` sobre la última ejecución reversible con éxito.
Archivo de 313 líneas.
Símbolos públicos observados:
- `pub struct ExecutionRecord`
- `pub struct Runner`
Tests en el mismo archivo: `toda_ejecucion_se_registra`, `irreversible_sin_aprobacion_no_ejecuta`, `undo_last_deshace_solo_reales_y_reversibles`, `run_que_paniquea_registra_fail`

## Para qué sirve

Puerto de `cortex/action_engine/runner.py` (Obra 05 Fase B).  Ejecuta acciones aplicando las reglas duras del contrato: - dry-run nativo (pasa `dry_run=true` al run de la acción); - irreversible ⇒ exige `approved=true` explícito; - toda ejecución (incluidos dry-runs y fallos) queda en action_log.jsonl; - deshacer: `undo_last()` sobre la última ejecución reversible con éxito.

## Relaciones

### Recibe de

- `use crate::models::{ahora_iso, Action, ActionResult, Trigger}`
- `use crate::store::{ActionLog, OrderedEntry}`
- `use crate::models::{Categoria, Costo}`
- Contexto de crate `cortex-actions`: cortex-app, cortex-enterprise, cortex-setup

### Envía a

- Crate `cortex-actions` envía hacia: cortex-cli next, cortex-companion, cortex-tui, .cortex/action_log.jsonl

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-actions/src/runner.rs`.
