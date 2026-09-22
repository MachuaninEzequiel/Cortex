# rust/crates/cortex-branding/src/wordmark.rs

## Qué tiene adentro

Wordmark "CORTEX" en pixel-font 3D estilo voxel isométrico.  Fuente de verdad visual: `assets/herdr-view/herdr-texto-formato.jpeg` (referencia Gentleman Dots). Gramática 3D por celda: `#` Mark      -> cara frontal SKY (`#89DCEB`) `H` Highlight -> bisel hielo arriba/izquierda (`#C8F0DC`) `L` Layer     -> extrusión derecha/inferior zafiro (`#04A5E5`) `S` Shadow    -> esquinas y segunda línea de la barra (`#1E3A5F`)  La matriz está precalculada (silueta 7x9 por letra con trazos de 2 px, extrusión desplazada (+1,+1) sobre toda la palabra, guiones de sombra en la base y barra underline doble sky/navy). Renderizada con semibloques
Archivo de 118 líneas.
Símbolos públicos observados:
- `pub const FACE: crate::Rgb = crate::Rgb(0x89, 0xDC, 0xEB)`
- `pub const BEVEL: crate::Rgb = crate::Rgb(0xC8, 0xF0, 0xDC)`
- `pub const EXTRUSION: crate::Rgb = crate::Rgb(0x04, 0xA5, 0xE5)`
- `pub const DEEP: crate::Rgb = crate::Rgb(0x1E, 0x3A, 0x5F)`
- `pub fn color_for(kind: PixelKind) -> Option<crate::Rgb>`
- `pub fn wordmark() -> &'static PixelMap`
Tests en el mismo archivo: `dimensiones_wordmark`, `pares_de_filas_llenos_para_halfblocks`, `gramatica_3d_coherente`, `underline_doble_al_final`, `color_for_cubre_todas_las_clases_del_mapa`

## Para qué sirve

Wordmark "CORTEX" en pixel-font 3D estilo voxel isométrico.  Fuente de verdad visual: `assets/herdr-view/herdr-texto-formato.jpeg` (referencia Gentleman Dots). Gramática 3D por celda: `#` Mark      -> cara frontal SKY (`#89DCEB`) `H` Highlight -> bisel hielo arriba/izquierda (`#C8F0DC`) `L` Layer     -> extrusión derecha/inferior zafiro (`#04A5E5`) `S` Shadow    -> esquinas y segunda línea de la barra (`#1E3A5F`)  La matriz está precalculada (silueta 7x9 por letra con trazos de 2 px, extrusión desplazada (+1,+1) sobre toda la palabra, guiones de sombra en la base y barra underline doble sky/navy). Renderizada con semibloques

## Relaciones

### Recibe de

- `use crate::pixels::{PixelKind, PixelMap}`
- `use crate::pixels::PixelKind`
- Contexto de crate `cortex-branding`: nada de otros crates Cortex

### Envía a

- Crate `cortex-branding` envía hacia: cortex-brain (banner), cortex-tui, cortex-companion

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-branding/src/wordmark.rs`.
