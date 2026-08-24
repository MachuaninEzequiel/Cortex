//! Color por píxel: gradiente separado de la geometría (prompt-logo.md §4, §9).
//!
//! El gradiente es una sola familia cromática vertical (hielo → cyan → azul);
//! las capas usan tonos levemente más profundos y la X va en LIGHT→CYAN.

use crate::palette::{self, Rgb};
use crate::pixels::PixelKind;

/// Color de un píxel según su clase y posición. `None` = transparente (el
/// renderer no pinta nada y respeta el fondo del usuario).
pub fn color_for(kind: PixelKind, y: usize, h: usize) -> Option<Rgb> {
    match kind {
        PixelKind::Transparent => None,
        // Estructura principal: gradiente vertical completo.
        PixelKind::Mark => Some(palette::gradient_at(y, h)),
        // X central: banda LIGHT→CYAN (prompt §4).
        PixelKind::Cross => Some(palette::LIGHT.lerp(palette::CYAN, frac(y, h))),
        // Capas: mismo gradiente corrido hacia abajo = tono más profundo sutil.
        PixelKind::Layer => Some(palette::gradient_at(y + h / 6, h)),
        // Highlights: el punto más brillante de la paleta.
        PixelKind::Highlight => Some(palette::ICE),
        // Glow periférico: azul noche, baja intensidad.
        PixelKind::Shadow => Some(palette::SHADOW),
    }
}

fn frac(y: usize, h: usize) -> f32 {
    if h <= 1 {
        0.0
    } else {
        (y as f32 / (h - 1) as f32).clamp(0.0, 1.0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn transparent_no_pinta() {
        assert_eq!(color_for(PixelKind::Transparent, 0, 10), None);
    }

    #[test]
    fn highlight_es_ice_y_shadow_es_shadow() {
        assert_eq!(color_for(PixelKind::Highlight, 5, 10), Some(palette::ICE));
        assert_eq!(color_for(PixelKind::Shadow, 5, 10), Some(palette::SHADOW));
    }

    #[test]
    fn cross_permanece_en_banda_light_cyan() {
        for y in [0, 3, 9] {
            let c = color_for(PixelKind::Cross, y, 10).unwrap();
            assert!(c != palette::DEEP && c != palette::BLUE);
        }
    }

    #[test]
    fn h_cero_o_uno_no_panic() {
        assert!(color_for(PixelKind::Mark, 0, 0).is_some());
        assert!(color_for(PixelKind::Layer, 0, 1).is_some());
    }
}
