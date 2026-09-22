# rust/crates/cortex-tui/src/splash.rs

## Qué tiene adentro

Splash de Cortex (prompt-logo.md §43): isotipo + wordmark + tagline.  Composición centrada que respira (§42); el fondo NUNCA se pinta (§26): el splash respeta la terminal del usuario. La tagline es un componente separado del logo (§14).
Archivo de 91 líneas.
Símbolos públicos observados:
- `pub fn tagline(lang: &str) -> &'static str`
- `pub fn render(f: &mut Frame<'_>, mode: ColorMode)`

## Para qué sirve

Splash de Cortex (prompt-logo.md §43): isotipo + wordmark + tagline.  Composición centrada que respira (§42); el fondo NUNCA se pinta (§26): el splash respeta la terminal del usuario. La tagline es un componente separado del logo (§14).

## Relaciones

### Recibe de

- `use crate::renderer::{render_pixel_map_with, CortexLogo}`
- `use crate::theme::Theme`
- `use crate::{branding_mode, lang, BrandingMode}`
- `use cortex_branding::ansi::ColorMode`
- `use cortex_branding::wordmark::{self, wordmark}`
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/splash.rs`.
