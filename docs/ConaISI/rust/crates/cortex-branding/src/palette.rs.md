# rust/crates/cortex-branding/src/palette.rs

## Qué tiene adentro

Paleta oficial de Cortex (identidad voxel esmeralda/menta/verde bosque).  Fuente de verdad: `assets/nueva-estetica/nuevo-logo-cortex.png`. No hardcodear colores en otros módulos: todo pasa por acá.
Archivo de 192 líneas.
Símbolos públicos observados:
- `pub struct Rgb(pub u8, pub u8, pub u8)`
- `pub const ICE: Rgb = Rgb(0xC8, 0xF0, 0xDC)`
- `pub const LIGHT: Rgb = Rgb(0xAE, 0xE8, 0xC6)`
- `pub const CYAN: Rgb = Rgb(0x8F, 0xDC, 0xB0)`
- `pub const BLUE: Rgb = Rgb(0x03, 0x52, 0x2E)`
- `pub const DEEP: Rgb = Rgb(0x06, 0x33, 0x1C)`
- `pub const SHADOW: Rgb = Rgb(0x04, 0x1C, 0x12)`
- `pub const TEXT: Rgb = Rgb(0xE4, 0xED, 0xE7)`
- `pub const MUTED: Rgb = Rgb(0x8A, 0x9E, 0x93)`
- `pub const BG: Rgb = Rgb(0x0C, 0x14, 0x10)`
- `pub const TEXT_PRIMARY: Rgb = Rgb(0xDF, 0xEB, 0xE7)`
- `pub const TEXT_MUTED: Rgb = Rgb(0x78, 0x96, 0x8E)`
- `pub const BORDER_IDLE: Rgb = Rgb(0x2A, 0x4A, 0x3A)`
- `pub const SURFACE_SUBTLE: Rgb = Rgb(0x0E, 0x24, 0x1E)`
- `pub const SUCCESS: Rgb = Rgb(0x4A, 0xDE, 0x80)`
- `pub const WARNING: Rgb = Rgb(0xFB, 0xBF, 0x24)`
- `pub const ERROR: Rgb = Rgb(0xF8, 0x71, 0x71)`
- `pub const GRADIENT_STOPS: [Rgb`
- `pub fn gradient_at(y: usize, h: usize) -> Rgb`
- `pub enum Ansi16`
- … y 1 más en el extracto
Tests en el mismo archivo: `lerp_extremos`, `gradiente_extremos_son_ice_y_deep`, `gradiente_h1_no_panic`, `fallback_cubierto`, `semantica_preserva_significado_en_16`

## Para qué sirve

Paleta oficial de Cortex (identidad voxel esmeralda/menta/verde bosque).  Fuente de verdad: `assets/nueva-estetica/nuevo-logo-cortex.png`. No hardcodear colores en otros módulos: todo pasa por acá.

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-branding`: nada de otros crates Cortex

### Envía a

- Crate `cortex-branding` envía hacia: cortex-brain (banner), cortex-tui, cortex-companion

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-branding/src/palette.rs`.
