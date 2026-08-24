//! Tests de geometría del branding (prompt-logo.md §45-46): dimensiones de
//! las máscaras, consistencia de las grillas y presencia de las regiones.

use cortex_branding::logo::{self, LogoVariant};
use cortex_branding::pixels::PixelKind;
use cortex_branding::wordmark::wordmark;

#[test]
fn dimensiones_de_las_tres_variantes() {
    // Dentro de los rangos del prompt §15-17:
    // Full 44-54 cols × 16-22 filas → 44×34 px = 44×17 filas ✓
    // Compact 26-34 × 10-14 → 28×20 px = 28×10 filas ✓
    // Mark 8-14 × 4-7 → 13×10 px = 13×5 filas ✓
    let (w, h) = (logo::full().w(), logo::full().h());
    assert_eq!((w, h), (44, 34));

    let (w, h) = (logo::compact().w(), logo::compact().h());
    assert_eq!((w, h), (28, 20));

    let (w, h) = (logo::mark().w(), logo::mark().h());
    assert_eq!((w, h), (13, 10));
}

#[test]
fn wordmark_35x7() {
    assert_eq!((wordmark().w(), wordmark().h()), (35, 7));
}

#[test]
fn full_tiene_glow_y_regiones_completas() {
    let full = logo::full();
    assert!(full.count(PixelKind::Shadow) > 0, "Full debe tener glow");
    assert!(full.count(PixelKind::Mark) > 100);
    assert!(full.count(PixelKind::Cross) > 20, "la X debe estar");
    assert!(full.count(PixelKind::Layer) > 10, "las capas deben estar");
    assert!(full.count(PixelKind::Highlight) > 0);
}

#[test]
fn compact_y_mark_no_tienen_glow() {
    assert_eq!(logo::compact().count(PixelKind::Shadow), 0);
    assert_eq!(logo::mark().count(PixelKind::Shadow), 0);
}

#[test]
fn mark_conserva_silueta_minima() {
    // Prompt §17/§38: incluso en Mark, C + X + capas deben leerse.
    let mark = logo::mark();
    assert!(mark.count(PixelKind::Mark) > 20);
    assert!(mark.count(PixelKind::Cross) > 5);
    assert!(mark.count(PixelKind::Layer) >= 3);
}

#[test]
fn variantes_exponen_su_mapa() {
    for variant in [LogoVariant::Full, LogoVariant::Compact, LogoVariant::Mark] {
        let map = variant.pixel_map();
        assert!(
            map.w() > 0 && map.h() > 0,
            "{}: mapa vacío",
            variant.label()
        );
    }
}

#[test]
fn silueta_identificable_en_un_solo_color() {
    // Prompt §38: sin gradiente la forma debe seguir siendo Cortex —
    // verificamos que la silueta (todo lo no-transparente) no sea vacía por
    // variante y que las capas queden a la IZQUIERDA de la estructura.
    for variant in [LogoVariant::Full, LogoVariant::Compact, LogoVariant::Mark] {
        let map = variant.pixel_map();
        let mut min_layer_x = usize::MAX;
        let mut min_mark_x = usize::MAX;
        for y in 0..map.h() {
            for x in 0..map.w() {
                match map.get(x, y) {
                    PixelKind::Layer => min_layer_x = min_layer_x.min(x),
                    PixelKind::Mark => min_mark_x = min_mark_x.min(x),
                    _ => {}
                }
            }
        }
        assert!(
            min_layer_x <= min_mark_x,
            "{}: las capas deben asomar por la izquierda",
            variant.label()
        );
    }
}
