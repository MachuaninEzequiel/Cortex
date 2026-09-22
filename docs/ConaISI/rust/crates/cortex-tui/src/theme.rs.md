# rust/crates/cortex-tui/src/theme.rs

## Qué tiene adentro

Única fuente de estilos del chrome TUI (spec §7.2).  Regla del rediseño: ningún `Color::Rgb(...)` fuera de `theme.rs` y `renderer.rs` (test de higiene en `tests/theme_hygiene.rs`). Los colores se resuelven acá según `ColorMode` (truecolor / 16 / plain) y se entregan como `Style` o `Block` ya listos para el render.  Semántica (spec §7.1): el azul identifica selección/actividad; los colores semánticos (success/warning/error) solo para estados, siempre acompañados de símbolo y texto (no dependen solo del color).
Archivo de 280 líneas.
Símbolos públicos observados:
- `pub enum StatusKind`
- `pub struct Theme`
- `pub fn brand_text(style: Style) -> ratatui::text::Line<'static>`
- `pub const MARK_MIN_WIDTH: u16 = 15`

## Para qué sirve

Única fuente de estilos del chrome TUI (spec §7.2).  Regla del rediseño: ningún `Color::Rgb(...)` fuera de `theme.rs` y `renderer.rs` (test de higiene en `tests/theme_hygiene.rs`). Los colores se resuelven acá según `ColorMode` (truecolor / 16 / plain) y se entregan como `Style` o `Block` ya listos para el render.  Semántica (spec §7.1): el azul identifica selección/actividad; los colores semánticos (success/warning/error) solo para estados, siempre acompañados de símbolo y texto (no dependen solo del color).

## Relaciones

### Recibe de

- `use cortex_branding::ansi::ColorMode`
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/theme.rs`.
