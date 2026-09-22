# rust/crates/cortex-tui/src/components/panel.rs

## Qué tiene adentro

Panel principal (spec §13): borde redondeado con título, idle/focus. El layout INTERNO nunca se decide acá — el caller compone.
Archivo de 51 líneas.
Símbolos públicos observados:
- `pub fn draw_panel(`
Tests en el mismo archivo: `panel_pinta_borde_y_deja_inner`

## Para qué sirve

Panel principal (spec §13): borde redondeado con título, idle/focus. El layout INTERNO nunca se decide acá — el caller compone.

## Relaciones

### Recibe de

- `use crate::theme::Theme`
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/components/panel.rs`.
