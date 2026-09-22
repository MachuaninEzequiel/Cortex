# rust/crates/cortex-tui/src/components/empty_state.rs

## Qué tiene adentro

Estado vacío (spec §13 EmptyState / §11.7): explica QUÉ falta y ofrece una acción concreta. Nunca un panel vacío sin explicación.
Archivo de 84 líneas.
Símbolos públicos observados:
- `pub struct EmptyState<'a>`
Tests en el mismo archivo: `empty_state_explica_y_ofrece_accion`

## Para qué sirve

Estado vacío (spec §13 EmptyState / §11.7): explica QUÉ falta y ofrece una acción concreta. Nunca un panel vacío sin explicación.

## Relaciones

### Recibe de

- `use crate::theme::{StatusKind, Theme}`
- `use cortex_branding::ansi::ColorMode`
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/components/empty_state.rs`.
