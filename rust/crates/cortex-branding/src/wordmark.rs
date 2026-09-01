//! Wordmark "CORTEX" en pixel-font 3D estilo voxel isométrico.
//!
//! Fuente de verdad visual: `assets/herdr-view/herdr-texto-formato.jpeg`
//! (referencia Gentleman Dots). Gramática 3D por celda:
//! * `#` Mark      -> cara frontal SKY (`#89DCEB`)
//! * `H` Highlight -> bisel hielo arriba/izquierda (`#C8F0DC`)
//! * `L` Layer     -> extrusión derecha/inferior zafiro (`#04A5E5`)
//! * `S` Shadow    -> esquinas y segunda línea de la barra (`#1E3A5F`)
//!
//! La matriz está precalculada (silueta 7x9 por letra con trazos de 2 px,
//! extrusión desplazada (+1,+1) sobre toda la palabra, guiones de sombra en
//! la base y barra underline doble sky/navy). Renderizada con semibloques
//! `▀`/`▄` ocupa 53 columnas x 7 filas. NO usar `gradient::color_for` para
//! el wordmark: esa familia es menta (isotipo del logo); el wordmark usa la
//! paleta fría propia de [`color_for`].

use crate::pixels::{PixelKind, PixelMap};
use std::sync::OnceLock;

/// Matriz completa del wordmark (53 x 14 px lógicos).
const ROWS: &[&str] = &[
    "..HHHH.....HHHH...HHHHH....HHHHHHH..HHHHHHH..HH...HH",
    "H.H##SH..H.H##SH..HSH##LH..H######L.H######L.H#L..H#L",
    "HH.LLL.L.HH.LLH#L.HH.LLH#L..LLHSLLL.H#SLLLLL..HLH.HSL",
    "H#L......H#L..H#L.H#L..H#L....HL....H#L........H.H.L",
    "H#L......H#L..H#L.H#HHH.LL....HL....H#HHH.......H.L",
    "H#L......H#L..H#L.H#SHSL......HL....H#SLLL.....H.H",
    "H#L......H#L..H#L.H#L.H.......HL....H#L.......H.H.H",
    "HSHHH.H..HSHHH.HL.H#L..H......HL....H#HHHHH..H#L.LHH",
    ".LH##H.L..LH##H.L.H#L...H.....HL....H######L.H#L..H#L",
    "...LLLL.....LLLL...LL....L.....L.....LLLLLLL..LL...LL",
    "",
    "####################################################",
    "",
    "SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSS",
];

/// Colores fríos propios del wordmark (identidad Herdr, no el isotipo menta).
pub const FACE: crate::Rgb = crate::Rgb(0x89, 0xDC, 0xEB); // sky
pub const BEVEL: crate::Rgb = crate::Rgb(0xC8, 0xF0, 0xDC); // hielo
pub const EXTRUSION: crate::Rgb = crate::Rgb(0x04, 0xA5, 0xE5); // zafiro
pub const DEEP: crate::Rgb = crate::Rgb(0x1E, 0x3A, 0x5F); // navy

/// Color del wordmark según clase de píxel. `None` = no pintar (fondo).
pub fn color_for(kind: PixelKind) -> Option<crate::Rgb> {
    match kind {
        PixelKind::Highlight => Some(BEVEL),
        PixelKind::Mark | PixelKind::Cross => Some(FACE),
        PixelKind::Layer => Some(EXTRUSION),
        PixelKind::Shadow => Some(DEEP),
        PixelKind::Transparent => None,
    }
}

/// "CORTEX" como `PixelMap` (53 x 14 px -> 53 cols x 7 filas con half-blocks).
pub fn wordmark() -> &'static PixelMap {
    static WORDMARK: OnceLock<PixelMap> = OnceLock::new();
    WORDMARK.get_or_init(|| PixelMap::parse(ROWS))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::pixels::PixelKind;

    #[test]
    fn dimensiones_wordmark() {
        let wm = wordmark();
        assert_eq!(wm.w(), 53);
        assert_eq!(wm.h(), 14);
    }

    #[test]
    fn pares_de_filas_llenos_para_halfblocks() {
        // Cada fila lógica par/impar debe producir celdas no vacías en su banda.
        let wm = wordmark();
        for row in 0..(wm.h() / 2) {
            let has = (0..wm.w()).any(|x| {
                wm.get(x, row * 2) != PixelKind::Transparent
                    || wm.get(x, row * 2 + 1) != PixelKind::Transparent
            });
            assert!(has, "banda de half-blocks {row} quedó vacía");
        }
    }

    #[test]
    fn gramatica_3d_coherente() {
        let wm = wordmark();
        // Cara, bevel, extrusión y sombra profunda presentes.
        assert!(wm.count(PixelKind::Mark) > 50);
        assert!(wm.count(PixelKind::Highlight) > 20);
        assert!(wm.count(PixelKind::Layer) > 20);
        assert!(wm.count(PixelKind::Shadow) > 20);
    }

    #[test]
    fn underline_doble_al_final() {
        let wm = wordmark();
        let fila_sky = wm.w() - 3;
        assert_eq!(wm.get(0, 11), PixelKind::Mark);
        assert_eq!(wm.get(fila_sky, 11), PixelKind::Mark);
        assert_eq!(wm.get(0, 13), PixelKind::Shadow);
        assert_eq!(wm.get(fila_sky, 13), PixelKind::Shadow);
    }

    #[test]
    fn color_for_cubre_todas_las_clases_del_mapa() {
        let wm = wordmark();
        for y in 0..wm.h() {
            for x in 0..wm.w() {
                let k = wm.get(x, y);
                if k != PixelKind::Transparent {
                    assert!(color_for(k).is_some(), "color faltante para {k:?}");
                }
            }
        }
    }
}
