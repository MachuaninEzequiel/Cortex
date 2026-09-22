# rust/crates/cortex-tui/src/event.rs

## Qué tiene adentro

Eventos y mapeo de teclas/mouse a acciones semánticas (spec §2).
Archivo de 28 líneas.
Símbolos públicos observados:
- `pub use crate::app::Action`
- `pub use crate::keymap::`
- `pub fn mouse_to_action(m: MouseEvent) -> Option<Action>`
- `pub fn map_event(event: Event, ctx: KeyContext) -> Option<Action>`

## Para qué sirve

Eventos y mapeo de teclas/mouse a acciones semánticas (spec §2).

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/event.rs`.
