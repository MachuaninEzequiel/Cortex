# rust/crates/cortex-branding/examples/preview.rs

## Qué tiene adentro

Preview de las tres variantes + wordmark (dev: `cargo run -p cortex-branding --example preview`). Colorea según entorno; respeta NO_COLOR.
Archivo de 36 líneas.

## Para qué sirve

Preview de las tres variantes + wordmark (dev: `cargo run -p cortex-branding --example preview`). Colorea según entorno; respeta NO_COLOR.

## Relaciones

### Recibe de

- `use cortex_branding::ansi::{self, ColorMode}`
- `use cortex_branding::logo::LogoVariant`
- `use cortex_branding::wordmark::wordmark`
- Contexto de crate `cortex-branding`: nada de otros crates Cortex

### Envía a

- Crate `cortex-branding` envía hacia: cortex-brain (banner), cortex-tui, cortex-companion

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-branding/examples/preview.rs`.
