# rust/crates/cortex-tui/src/app/action.rs

## Qué tiene adentro

Acciones SEMÁNTICAS (spec §5): el keymap traduce teclas → `Action`; el reducer decide transiciones. Ninguna pantalla hace `match KeyCode`. Acción semántica producida por el keymap o el runtime.
Archivo de 115 líneas.
Símbolos públicos observados:
- `pub enum Action`
Tests en el mismo archivo: `acciones_son_comparables`

## Para qué sirve

Acciones SEMÁNTICAS (spec §5): el keymap traduce teclas → `Action`; el reducer decide transiciones. Ninguna pantalla hace `match KeyCode`. Acción semántica producida por el keymap o el runtime.

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/app/action.rs`.
