# cortex/action_engine/runner.py

## Qué tiene adentro

- `ExecutionRecord` (action, result, duration_ms, dry_run).
- `Runner(directory, trigger="on-open")` con `ActionLog`.
- `execute(action, dry_run=False, approved=False, via="user")`:
  - irreversible exige `approved=True` salvo dry-run;
  - **siempre** registra en `action_log.jsonl` (éxito, fallo, dry-run);
  - `undo_last()` para la última ejecución reversible ok.

## Para qué sirve

Ejecutor único del ciclo OBSERVAR→PROPONER→APROBAR→EJECUTAR→APRENDER. Las acciones delegan a servicios existentes; el runner aplica el contrato.

## Relaciones

### Recibe de

- `Action` / `ActionResult` (`models`).
- `ActionLog` (`store`) en un directorio (`.cortex`).
- Acciones del catálogo (`actions/catalog.py`).

### Envía a

- `.cortex/action_log.jsonl`.
- TUI (`cortex.tui.core`) y CLI `cortex next`.

---
Fuente: lectura de `cortex/action_engine/runner.py`. No se usó documentación previa.
