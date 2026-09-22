# rust/crates/cortex-branding/src/ansi.rs

## Qué tiene adentro

Render half-block a ANSI plano (prompt-logo.md §7, §10, §24-26).  Convierte `PixelMap` a strings con `▀`/`▄`/`█` y colores truecolor o 16. Es la vía SIN ratatui (banner del brain, previews); la integración como `Widget` vive en `cortex-tui`. Fondo siempre `Reset` en celdas transparentes: jamás se pinta el fondo del usuario (prompt §26).
Archivo de 210 líneas.
Símbolos públicos observados:
- `pub enum ColorMode`
- `pub fn env_color_mode() -> ColorMode`
- `pub fn should_color() -> bool`
- `pub fn render_ansi(map: &PixelMap, mode: ColorMode) -> String`
- `pub fn render_plain(map: &PixelMap) -> String`
- `pub fn visible_width(s: &str) -> usize`
Tests en el mismo archivo: `dimensiones_del_render`, `ansi_no_cuenta_escapes_como_ancho`, `plain_no_tiene_escapes`, `visible_width_basico`

## Para qué sirve

Render half-block a ANSI plano (prompt-logo.md §7, §10, §24-26).  Convierte `PixelMap` a strings con `▀`/`▄`/`█` y colores truecolor o 16. Es la vía SIN ratatui (banner del brain, previews); la integración como `Widget` vive en `cortex-tui`. Fondo siempre `Reset` en celdas transparentes: jamás se pinta el fondo del usuario (prompt §26).

## Relaciones

### Recibe de

- `use crate::gradient::color_for`
- `use crate::palette::{self, Rgb}`
- `use crate::pixels::{PixelKind, PixelMap}`
- `use crate::logo`
- Contexto de crate `cortex-branding`: nada de otros crates Cortex

### Envía a

- Crate `cortex-branding` envía hacia: cortex-brain (banner), cortex-tui, cortex-companion

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-branding/src/ansi.rs`.
