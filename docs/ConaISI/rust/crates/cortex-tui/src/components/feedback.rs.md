# rust/crates/cortex-tui/src/components/feedback.rs

## Qué tiene adentro

Feedback efímero dentro de la TUI (spec §13): toast/banner, nunca `println!` sobre alternate screen. Los errores persisten hasta acción del usuario; los éxitos expiran (ver `app::update::expire_notifications`).
Archivo de 41 líneas.
Símbolos públicos observados:
- `pub use crate::app::state::Notification`
- `pub fn message_line(`
Tests en el mismo archivo: `linea_lleva_glyph_y_texto`

## Para qué sirve

Feedback efímero dentro de la TUI (spec §13): toast/banner, nunca `println!` sobre alternate screen. Los errores persisten hasta acción del usuario; los éxitos expiran (ver `app::update::expire_notifications`).

## Relaciones

### Recibe de

- `use crate::theme::{StatusKind, Theme}`
- `use cortex_branding::ansi::ColorMode`
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/components/feedback.rs`.
