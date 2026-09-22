# rust/crates/cortex-branding/src/gradient.rs

## Qué tiene adentro

Color por píxel: gradiente separado de la geometría (prompt-logo.md §4, §9).  El gradiente es una sola familia cromática vertical (hielo → cyan → azul); las capas usan tonos levemente más profundos y la X va en LIGHT→CYAN.
Archivo de 63 líneas.
Símbolos públicos observados:
- `pub fn color_for(kind: PixelKind, y: usize, h: usize) -> Option<Rgb>`
Tests en el mismo archivo: `transparent_no_pinta`, `highlight_es_ice_y_shadow_es_shadow`, `cross_permanece_en_banda_light_cyan`, `h_cero_o_uno_no_panic`

## Para qué sirve

Color por píxel: gradiente separado de la geometría (prompt-logo.md §4, §9).  El gradiente es una sola familia cromática vertical (hielo → cyan → azul); las capas usan tonos levemente más profundos y la X va en LIGHT→CYAN.

## Relaciones

### Recibe de

- `use crate::palette::{self, Rgb}`
- `use crate::pixels::PixelKind`
- Contexto de crate `cortex-branding`: nada de otros crates Cortex

### Envía a

- Crate `cortex-branding` envía hacia: cortex-brain (banner), cortex-tui, cortex-companion

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-branding/src/gradient.rs`.
