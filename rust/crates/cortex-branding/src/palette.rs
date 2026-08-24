//! Paleta oficial de Cortex (identidad monocromática azul/cyan fría).
//!
//! Fuente de verdad: `docs/logo/prompt-logo.md` §3 (aprobada por el dueño).
//! No hardcodear colores en otros módulos: todo pasa por acá.

/// Color RGB simple, sin dependencias externas.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct Rgb(pub u8, pub u8, pub u8);

impl Rgb {
    pub fn lerp(self, other: Rgb, t: f32) -> Rgb {
        let t = t.clamp(0.0, 1.0);
        Rgb(
            (self.0 as f32 + (other.0 as f32 - self.0 as f32) * t).round() as u8,
            (self.1 as f32 + (other.1 as f32 - self.1 as f32) * t).round() as u8,
            (self.2 as f32 + (other.2 as f32 - self.2 as f32) * t).round() as u8,
        )
    }
}

// ── Gradiente del isotipo (hielo → cyan → azul eléctrico) ──

/// Blanco azulado (puntas más altas / highlights).
pub const ICE: Rgb = Rgb(0xD9, 0xF4, 0xFF);
/// Cyan claro.
pub const LIGHT: Rgb = Rgb(0xA9, 0xE3, 0xFF);
/// Cyan principal.
pub const CYAN: Rgb = Rgb(0x55, 0xCA, 0xF7);
/// Azul eléctrico.
pub const BLUE: Rgb = Rgb(0x20, 0x9C, 0xEB);
/// Azul profundo (base inferior).
pub const DEEP: Rgb = Rgb(0x11, 0x67, 0xC4);
/// Glow periférico (azul noche).
pub const SHADOW: Rgb = Rgb(0x0B, 0x31, 0x58);

// ── Texto y fondo de referencia ──

/// Texto principal.
pub const TEXT: Rgb = Rgb(0xD9, 0xF4, 0xFF);
/// Texto secundario.
pub const MUTED: Rgb = Rgb(0x6E, 0x89, 0x9B);
/// Fondo de referencia (SOLO para screens que decidan fondo propio; jamás
/// pintar la terminal del usuario — ver prompt §26).
pub const BG: Rgb = Rgb(0x05, 0x0A, 0x10);

/// Stops del gradiente vertical del isotipo, de arriba hacia abajo.
pub const GRADIENT_STOPS: [Rgb; 5] = [ICE, LIGHT, CYAN, BLUE, DEEP];

/// Color del gradiente vertical en `y` normalizado a `[0, h-1]`.
pub fn gradient_at(y: usize, h: usize) -> Rgb {
    if h <= 1 {
        return GRADIENT_STOPS[0];
    }
    let t = (y as f32 / (h - 1) as f32) * (GRADIENT_STOPS.len() - 1) as f32;
    let i = (t as usize).min(GRADIENT_STOPS.len() - 2);
    GRADIENT_STOPS[i].lerp(GRADIENT_STOPS[i + 1], t - i as f32)
}

// ── Fallback para terminales sin truecolor (prompt §25) ──

/// Color ANSI de 16 para terminales limitadas.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Ansi16 {
    DarkGray,
    LightCyan,
    Cyan,
    Blue,
    White,
}

/// Mapeo de fallback acordado (prompt §25): Ice→Cyan, Light→LightCyan,
/// Cyan→Cyan, Blue→Blue, Deep→DarkGray.
pub fn fallback(rgb: Rgb) -> Ansi16 {
    if rgb == ICE || rgb == CYAN {
        Ansi16::Cyan
    } else if rgb == LIGHT || rgb == TEXT {
        Ansi16::LightCyan
    } else if rgb == BLUE {
        Ansi16::Blue
    } else if rgb == MUTED || rgb == SHADOW || rgb == DEEP || rgb == BG {
        Ansi16::DarkGray
    } else {
        Ansi16::White
    }
}

impl Ansi16 {
    /// Código SGR de foreground (30-37 / 90-97).
    pub const fn fg_code(self) -> u8 {
        match self {
            Ansi16::DarkGray => 90,
            Ansi16::LightCyan => 96,
            Ansi16::Cyan => 36,
            Ansi16::Blue => 34,
            Ansi16::White => 97,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn lerp_extremos() {
        assert_eq!(ICE.lerp(DEEP, 0.0), ICE);
        assert_eq!(ICE.lerp(DEEP, 1.0), DEEP);
    }

    #[test]
    fn gradiente_extremos_son_ice_y_deep() {
        assert_eq!(gradient_at(0, 34), ICE);
        assert_eq!(gradient_at(33, 34), DEEP);
    }

    #[test]
    fn gradiente_h1_no_panic() {
        assert_eq!(gradient_at(0, 1), ICE);
    }

    #[test]
    fn fallback_cubierto() {
        for rgb in [ICE, LIGHT, CYAN, BLUE, DEEP, SHADOW, TEXT, MUTED, BG] {
            let _ = fallback(rgb);
        }
    }
}
