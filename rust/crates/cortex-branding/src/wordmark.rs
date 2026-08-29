//! Wordmark "CORTEX" en pixel-font 3D isométrica voxel (5×7).
//!
//! Fuente de verdad: `assets/nueva-estetica/nuevo-logo-cortex.png`.
//! 'H'=Highlight (cara superior iluminada -> ICE),
//! '#'=Mark (cara frontal blanca/menta -> ICE/TEXT),
//! 'L'=Layer (sombra 3D derecha/inferior -> DEEP/SHADOW).

use crate::pixels::{PixelKind, PixelMap};
use std::sync::OnceLock;

static GLYPHS: &[(&str, [&str; 7])] = &[
    (
        "C",
        [
            "HHHH.",
            "#..HL",
            "#...L",
            "#...L",
            "#...L",
            "#..HL",
            "####L",
        ],
    ),
    (
        "O",
        [
            "HHHH.",
            "#..HL",
            "#..HL",
            "#..HL",
            "#..HL",
            "#..HL",
            "####L",
        ],
    ),
    (
        "R",
        [
            "HHHH.",
            "#..HL",
            "#..HL",
            "####L",
            "#..HL",
            "#..HL",
            "#...L",
        ],
    ),
    (
        "T",
        [
            "HHHHH",
            "..#..",
            "..#..",
            "..#..",
            "..#..",
            "..#..",
            "..#..",
        ],
    ),
    (
        "E",
        [
            "HHHH.",
            "#...L",
            "#...L",
            "####L",
            "#...L",
            "#...L",
            "####L",
        ],
    ),
    (
        "X",
        [
            "#...#",
            ".#.#L",
            "..#..",
            "..#..",
            ".#.#L",
            "#...#",
            "#...#",
        ],
    ),
];

fn glyph(ch: char) -> Option<&'static [&'static str; 7]> {
    let upper = ch.to_ascii_uppercase();
    GLYPHS
        .iter()
        .find(|(name, _)| name.starts_with(upper))
        .map(|(_, rows)| rows)
}

/// "CORTEX" como `PixelMap` (35×7 px -> 35 cols x 4 filas con half-blocks).
pub fn wordmark() -> &'static PixelMap {
    static WORDMARK: OnceLock<PixelMap> = OnceLock::new();
    WORDMARK.get_or_init(|| {
        const LETTERS: &str = "CORTEX";
        const GLYPH_W: usize = 5;
        const GAP: usize = 1;
        let w = LETTERS.len() * GLYPH_W + (LETTERS.len() - 1) * GAP;
        let mut map = PixelMap::new(w, 7);
        for (i, ch) in LETTERS.chars().enumerate() {
            let rows = glyph(ch).unwrap_or_else(|| panic!("glifo faltante: {ch}"));
            let ox = i * (GLYPH_W + GAP);
            for (y, row) in rows.iter().enumerate() {
                for (x, ch) in row.chars().enumerate() {
                    let kind = match ch {
                        '#' => PixelKind::Mark,
                        'H' => PixelKind::Highlight,
                        'L' => PixelKind::Layer,
                        'X' => PixelKind::Cross,
                        _ => PixelKind::Transparent,
                    };
                    if kind != PixelKind::Transparent {
                        *map.get_mut(ox + x, y) = kind;
                    }
                }
            }
        }
        map
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::pixels::PixelKind;

    #[test]
    fn dimensiones_wordmark() {
        let wm = wordmark();
        assert_eq!(wm.w(), 35);
        assert_eq!(wm.h(), 7);
    }

    #[test]
    fn todos_los_glifos_presentes() {
        for ch in "CORTEX".chars() {
            assert!(glyph(ch).is_some(), "falta glifo {ch}");
        }
    }

    #[test]
    fn silueta_no_vacia_y_contenida() {
        let wm = wordmark();
        assert!(wm.count(PixelKind::Mark) > 10);
        assert!(wm.count(PixelKind::Highlight) > 5);
        assert_eq!(wm.get(4, 0), PixelKind::Transparent);
    }
}
