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

/// Texto principal del chrome TUI (identidad de marca, prompt §3).
pub const TEXT: Rgb = Rgb(0xD9, 0xF4, 0xFF);
/// Texto secundario del chrome TUI (identidad de marca).
pub const MUTED: Rgb = Rgb(0x6E, 0x89, 0x9B);
/// Fondo de referencia (SOLO para screens que decidan fondo propio; jamás
/// pintar la terminal del usuario — ver prompt §26).
pub const BG: Rgb = Rgb(0x05, 0x0A, 0x10);

// ── Semántica del chrome TUI (spec rediseño: tokens desaturados, pocos, ──
// ── centralizados; el azul identifica selección/actividad, no decora) ────

/// Texto normal de pantallas de datos.
pub const TEXT_PRIMARY: Rgb = Rgb(0xD8, 0xDE, 0xE9);
/// Metadatos, ayudas y etiquetas pasivas.
pub const TEXT_MUTED: Rgb = Rgb(0x7F, 0x8C, 0x9D);
/// Borde de panel sin foco.
pub const BORDER_IDLE: Rgb = Rgb(0x35, 0x40, 0x52);
/// Fondo de selección sutil (solo con color real; respeta fondo del usuario).
pub const SURFACE_SUBTLE: Rgb = Rgb(0x18, 0x20, 0x2B);
/// Éxito (semántico; nunca para categorías arbitrarias).
pub const SUCCESS: Rgb = Rgb(0x7B, 0xC9, 0x9B);
/// Advertencia (semántico; reemplaza el ámbar ad-hoc del Home).
pub const WARNING: Rgb = Rgb(0xE4, 0xB8, 0x6A);
/// Error (semántico).
pub const ERROR: Rgb = Rgb(0xE0, 0x6C, 0x75);
// Info == CYAN: la marca no duplica consts — un solo token por color.

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
    Green,
    Yellow,
    Red,
}

/// Mapeo de fallback acordado (prompt §25): Ice→Cyan, Light→LightCyan,
/// Cyan→Cyan, Blue→Blue, Deep→DarkGray. La semántica (spec rediseño)
/// conserva su significado en 16 colores: Success→Green, Warning→Yellow,
/// Error→Red. Todo lo demás cae en la escala neutra.
pub fn fallback(rgb: Rgb) -> Ansi16 {
    if rgb == ICE || rgb == CYAN {
        Ansi16::Cyan
    } else if rgb == LIGHT || rgb == TEXT || rgb == TEXT_PRIMARY {
        Ansi16::LightCyan
    } else if rgb == BLUE {
        Ansi16::Blue
    } else if rgb == SUCCESS {
        Ansi16::Green
    } else if rgb == WARNING {
        Ansi16::Yellow
    } else if rgb == ERROR {
        Ansi16::Red
    } else if rgb == MUTED
        || rgb == TEXT_MUTED
        || rgb == SHADOW
        || rgb == DEEP
        || rgb == BG
        || rgb == BORDER_IDLE
        || rgb == SURFACE_SUBTLE
    {
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
            Ansi16::Green => 92,
            Ansi16::Yellow => 93,
            Ansi16::Red => 91,
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
        for rgb in [
            ICE,
            LIGHT,
            CYAN,
            BLUE,
            DEEP,
            SHADOW,
            TEXT,
            MUTED,
            BG,
            TEXT_PRIMARY,
            TEXT_MUTED,
            BORDER_IDLE,
            SURFACE_SUBTLE,
            SUCCESS,
            WARNING,
            ERROR,
        ] {
            let _ = fallback(rgb);
        }
    }

    #[test]
    fn semantica_preserva_significado_en_16() {
        assert_eq!(fallback(SUCCESS), Ansi16::Green);
        assert_eq!(fallback(WARNING), Ansi16::Yellow);
        assert_eq!(fallback(ERROR), Ansi16::Red);
        assert_eq!(fallback(TEXT_PRIMARY), Ansi16::LightCyan);
        assert_eq!(fallback(TEXT_MUTED), Ansi16::DarkGray);
        assert_eq!(fallback(BORDER_IDLE), Ansi16::DarkGray);
    }
}
