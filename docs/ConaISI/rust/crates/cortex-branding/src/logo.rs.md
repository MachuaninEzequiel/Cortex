# rust/crates/cortex-branding/src/logo.rs

## Qué tiene adentro

Geometría del isotipo Cortex Voxel 3D Isométrico.  Fuente de verdad: `assets/nueva-estetica/nuevo-logo-cortex.png`. - Bloques superiores blancos/menta ('H' -> ICE, '#' -> TEXT) - Núcleo brillante ('X' -> CYAN menta) - Estantes inferiores esmeralda ('L' -> BLUE/CYAN) - Sombras 3D ('S' -> DEEP sombra)
Archivo de 134 líneas.
Símbolos públicos observados:
- `pub enum LogoVariant`
- `pub(crate) const FULL_ROWS: &[&str] = &[`
- `pub(crate) const COMPACT_ROWS: &[&str] = &[`
- `pub(crate) const MARK_ROWS: &[&str] = &[`
- `pub fn full() -> &'static PixelMap`
- `pub fn compact() -> &'static PixelMap`
- `pub fn mark() -> &'static PixelMap`

## Para qué sirve

Geometría del isotipo Cortex Voxel 3D Isométrico.  Fuente de verdad: `assets/nueva-estetica/nuevo-logo-cortex.png`. - Bloques superiores blancos/menta ('H' -> ICE, '#' -> TEXT) - Núcleo brillante ('X' -> CYAN menta) - Estantes inferiores esmeralda ('L' -> BLUE/CYAN) - Sombras 3D ('S' -> DEEP sombra)

## Relaciones

### Recibe de

- `use crate::pixels::PixelMap`
- Contexto de crate `cortex-branding`: nada de otros crates Cortex

### Envía a

- Crate `cortex-branding` envía hacia: cortex-brain (banner), cortex-tui, cortex-companion

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-branding/src/logo.rs`.
