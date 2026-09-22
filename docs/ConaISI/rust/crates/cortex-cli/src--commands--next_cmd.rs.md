# rust/crates/cortex-cli/src/commands/next_cmd.rs

## Qué tiene adentro

`cortex next`: evalúa `build_default_registry` + `Scheduler` + `ActionContext`. Flags `--all --json --explain-why-not --stats --tui`. `--tui` abre pantalla Actions de cortex-tui.

## Para qué sirve

Proponer próximas acciones (motor cortex-actions P6).

## Relaciones

### Recibe de

- `cortex_actions::{catalog, context, metrics, scheduler, store}`.
- ActionLog / PreferencesStore en `.cortex`.

### Envía a

- stdout propuestas; TUI aprobación.

### Notas de implementación observadas en el código

`elapsed_ms` es medición propia (normalizable `{{ELAPSED}}` en gates).
