# rust/crates/cortex-tui/src/components/status_bar.rs

## Qué tiene adentro

Barra de estado (spec §10): atajos prioritarios (tecla en azul suave, descripción muted), posición de lista y mensajes efímeros con prioridad semántica. Una línea delgada.
Archivo de 112 líneas.
Símbolos públicos observados:
- `pub struct StatusBar<'a>`
Tests en el mismo archivo: `hints_posicion_y_mensaje_conviven`

## Para qué sirve

Barra de estado (spec §10): atajos prioritarios (tecla en azul suave, descripción muted), posición de lista y mensajes efímeros con prioridad semántica. Una línea delgada.

## Relaciones

### Recibe de

- `use crate::app::state::Notification`
- `use crate::theme::Theme`
- `use crate::theme::StatusKind`
- `use cortex_branding::ansi::ColorMode`
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/components/status_bar.rs`.
