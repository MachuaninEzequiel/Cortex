# rust/crates/cortex-tui/src/renderer.rs

## Qué tiene adentro

Conversión píxeles lógicos → celdas ratatui (prompt-logo.md §10-12).  Un `PixelMap` se pinta con half-blocks: cada celda de terminal representa dos píxeles verticales (`▀` con fg=superior y bg=inferior). Celdas transparentes usan fondo `Reset`: jamás se pinta el fondo del usuario.
Archivo de 136 líneas.
Símbolos públicos observados:
- `pub struct CortexLogo`
- `pub fn render_pixel_map(map: &PixelMap, mode: ColorMode, area: Rect, buf: &mut Buffer)`
- `pub fn render_pixel_map_with(`
- `pub fn to_ratatui(c: Rgb, mode: ColorMode) -> Color`

## Para qué sirve

Conversión píxeles lógicos → celdas ratatui (prompt-logo.md §10-12).  Un `PixelMap` se pinta con half-blocks: cada celda de terminal representa dos píxeles verticales (`▀` con fg=superior y bg=inferior). Celdas transparentes usan fondo `Reset`: jamás se pinta el fondo del usuario.

## Relaciones

### Recibe de

- `use cortex_branding::ansi::ColorMode`
- `use cortex_branding::logo::LogoVariant`
- `use cortex_branding::palette::{self, Ansi16, Rgb}`
- `use cortex_branding::pixels::{PixelKind, PixelMap}`
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/renderer.rs`.
