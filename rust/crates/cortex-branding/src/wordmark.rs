//! Wordmark "Cortex" en pixel-font propia 5×7 (prompt-logo.md §20-21).
//!
//! Independiente del isotipo: se renderiza con el mismo half-block renderer
//! para que el branding se vea idéntico en cualquier terminal. Solo se definen
//! los glifos que la marca necesita.

use crate::pixels::PixelMap;
use std::sync::OnceLock;

/// Glifos 5×7 (filas, de arriba hacia abajo). `'.'`/`' '` = vacío.
/// `static` (no `const`) para que los glifos tengan préstamo `'static`.
static GLYPHS: &[(&str, [&str; 7])] = &[
    (
        "C",
        [
            ".###.", "#...#", "#....", "#....", "#....", "#...#", ".###.",
        ],
    ),
    (
        "o",
        [
            ".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###.",
        ],
    ),
    (
        "r",
        [
            ".....", ".....", "#.##.", "##..#", "#....", "#....", "#....",
        ],
    ),
    (
        "t",
        [
            ".....", ".#...", "###..", ".#...", ".#...", ".#...", "..##.",
        ],
    ),
    (
        "e",
        [
            ".....", ".....", ".###.", "#...#", "#####", "#....", ".###.",
        ],
    ),
    (
        "x",
        [
            ".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#",
        ],
    ),
];

fn glyph(ch: char) -> Option<&'static [&'static str; 7]> {
    GLYPHS
        .iter()
        .find(|(name, _)| name.starts_with(ch))
        .map(|(_, rows)| rows)
}

/// "Cortex" como `PixelMap` (35×7 px → 35 cols × 4 filas con half-blocks).
/// Computado una sola vez (el wordmark es estático, prompt §47).
pub fn wordmark() -> &'static PixelMap {
    static WORDMARK: OnceLock<PixelMap> = OnceLock::new();
    WORDMARK.get_or_init(|| {
        const LETTERS: &str = "Cortex";
        const GLYPH_W: usize = 5;
        const GAP: usize = 1;
        let w = LETTERS.len() * GLYPH_W + (LETTERS.len() - 1) * GAP;
        let mut map = PixelMap::new(w, 7);
        for (i, ch) in LETTERS.chars().enumerate() {
            let rows = glyph(ch).unwrap_or_else(|| panic!("glifo faltante: {ch}"));
            let ox = i * (GLYPH_W + GAP);
            for (y, row) in rows.iter().enumerate() {
                for (x, ch) in row.chars().enumerate() {
                    if ch == '#' {
                        *map.get_mut(ox + x, y) = crate::pixels::PixelKind::Mark;
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
        for ch in "Cortex".chars() {
            assert!(glyph(ch).is_some(), "falta glifo {ch}");
        }
    }

    #[test]
    fn silueta_no_vacia_y_contenida() {
        let wm = wordmark();
        assert!(wm.count(PixelKind::Mark) > 20);
        assert_eq!(wm.get(0, 0), PixelKind::Transparent);
    }
}
