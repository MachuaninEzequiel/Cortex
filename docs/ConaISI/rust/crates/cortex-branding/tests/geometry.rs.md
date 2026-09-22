# rust/crates/cortex-branding/tests/geometry.rs

## Qué tiene adentro

Tests de geometría del branding (prompt-logo.md §45-46): dimensiones de las máscaras, consistencia de las grillas y presencia de las regiones.
Archivo de 91 líneas.
Tests en el mismo archivo: `dimensiones_de_las_tres_variantes`, `wordmark_53x14`, `full_tiene_glow_y_regiones_completas`, `compact_y_mark_no_tienen_glow`, `mark_conserva_silueta_minima`, `variantes_exponen_su_mapa`, `silueta_identificable_en_un_solo_color`

## Para qué sirve

Tests de geometría del branding (prompt-logo.md §45-46): dimensiones de las máscaras, consistencia de las grillas y presencia de las regiones.

## Relaciones

### Recibe de

- `use cortex_branding::logo::{self, LogoVariant}`
- `use cortex_branding::pixels::PixelKind`
- `use cortex_branding::wordmark::wordmark`
- Contexto de crate `cortex-branding`: nada de otros crates Cortex

### Envía a

- Crate `cortex-branding` envía hacia: cortex-brain (banner), cortex-tui, cortex-companion

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-branding/tests/geometry.rs`.
