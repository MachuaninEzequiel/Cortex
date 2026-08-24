//! Render half-block a ANSI plano (prompt-logo.md §7, §10, §24-26).
//!
//! Convierte `PixelMap` a strings con `▀`/`▄`/`█` y colores truecolor o 16.
//! Es la vía SIN ratatui (banner del brain, previews); la integración como
//! `Widget` vive en `cortex-tui`. Fondo siempre `Reset` en celdas
//! transparentes: jamás se pinta el fondo del usuario (prompt §26).

use crate::gradient::color_for;
use crate::palette::{self, Rgb};
use crate::pixels::{PixelKind, PixelMap};

/// Modo de color del render.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum ColorMode {
    /// 24-bit (experiencia ideal, prompt §24).
    Truecolor,
    /// 16 colores para terminales limitadas (prompt §25).
    Ansi16,
    /// Silueta sin color (NO_COLOR, piped, etc.): la forma identifica sola
    /// (prompt §38).
    Plain,
}

/// Detección por entorno: `NO_COLOR` gana; `COLORTERM`/`TERM` con truecolor →
/// `Truecolor`; resto → `Ansi16` (conservador).
pub fn env_color_mode() -> ColorMode {
    if std::env::var_os("NO_COLOR").is_some_and(|v| !v.is_empty()) {
        return ColorMode::Plain;
    }
    for var in ["COLORTERM", "TERM"] {
        if let Ok(v) = std::env::var(var) {
            let v = v.to_ascii_lowercase();
            if v.contains("truecolor") || v.contains("24bit") {
                return ColorMode::Truecolor;
            }
        }
    }
    ColorMode::Ansi16
}

/// ¿Corresponde colorear en este contexto? (tty + NO_COLOR respetado).
pub fn should_color() -> bool {
    use std::io::IsTerminal;
    std::io::stdout().is_terminal() && env_color_mode() != ColorMode::Plain
}

/// Renderiza el mapa a string ANSI multi-línea (sin `\n` final).
pub fn render_ansi(map: &PixelMap, mode: ColorMode) -> String {
    let (w, h) = (map.w(), map.h());
    let mut out = String::with_capacity(w * h * 8);
    for y in (0..h).step_by(2) {
        for x in 0..w {
            let top = map.get(x, y);
            let bottom = map.get(x, y + 1);
            emit_cell(&mut out, top, bottom, y, h, mode);
        }
        if y + 2 < h {
            out.push_str("\x1b[0m\n");
        }
    }
    out.push_str("\x1b[0m");
    out
}

/// Silueta monocroma: misma geometría, cero escapes (prompt §38). El glow
/// (shadow) no se dibuja: la silueta es solo estructura.
pub fn render_plain(map: &PixelMap) -> String {
    let (w, h) = (map.w(), map.h());
    let mut out = String::with_capacity(w * h / 2 + h);
    for y in (0..h).step_by(2) {
        for x in 0..w {
            let (top, bottom) = (map.get(x, y), map.get(x, y + 1));
            match (top, bottom) {
                (PixelKind::Transparent | PixelKind::Shadow, PixelKind::Transparent | PixelKind::Shadow) => {
                    out.push(' ')
                }
                (PixelKind::Transparent | PixelKind::Shadow, _) => out.push('▄'),
                (_, PixelKind::Transparent | PixelKind::Shadow) => out.push('▀'),
                _ => out.push('█'),
            }
        }
        if y + 2 < h {
            out.push('\n');
        }
    }
    out
}

fn emit_cell(
    out: &mut String,
    top: PixelKind,
    bottom: PixelKind,
    y: usize,
    h: usize,
    mode: ColorMode,
) {
    let c_top = color_for(top, y, h);
    let c_bottom = color_for(bottom, y + 1, h);
    match (c_top, c_bottom) {
        (None, None) => out.push(' '),
        (Some(t), None) => {
            push_fg(out, t, mode);
            out.push('▀');
        }
        (None, Some(b)) => {
            push_fg(out, b, mode);
            out.push('▄');
        }
        (Some(t), Some(b)) if t == b => {
            push_fg(out, t, mode);
            out.push('█');
        }
        (Some(t), Some(b)) => {
            push_fg(out, t, mode);
            push_bg(out, b, mode);
            out.push('▀');
        }
    }
}

fn push_fg(out: &mut String, c: Rgb, mode: ColorMode) {
    match mode {
        ColorMode::Truecolor => {
            out.push_str(&format!("\x1b[38;2;{};{};{}m", c.0, c.1, c.2));
        }
        ColorMode::Ansi16 => {
            out.push_str(&format!("\x1b[{}m", palette::fallback(c).fg_code()));
        }
        ColorMode::Plain => {}
    }
}

fn push_bg(out: &mut String, c: Rgb, mode: ColorMode) {
    match mode {
        ColorMode::Truecolor => {
            out.push_str(&format!("\x1b[48;2;{};{};{}m", c.0, c.1, c.2));
        }
        // 16 colores: códigos de background 40-47/100-107 (fg_code + 10).
        ColorMode::Ansi16 => {
            out.push_str(&format!("\x1b[{}m", palette::fallback(c).fg_code() + 10));
        }
        ColorMode::Plain => {}
    }
}

/// Ancho VISIBLE de un string ANSI (escapes `\x1b[...m` fuera).
pub fn visible_width(s: &str) -> usize {
    let mut count = 0usize;
    let mut chars = s.chars().peekable();
    while let Some(ch) = chars.next() {
        if ch == '\x1b' && chars.peek() == Some(&'[') {
            chars.next();
            for c in chars.by_ref() {
                if c == 'm' {
                    break;
                }
            }
        } else {
            count += 1;
        }
    }
    count
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::logo;

    #[test]
    fn dimensiones_del_render() {
        for (map, variant) in [
            (logo::full(), "full"),
            (logo::compact(), "compact"),
            (logo::mark(), "mark"),
        ] {
            let plain = render_plain(map);
            let lines: Vec<&str> = plain.lines().collect();
            assert_eq!(
                lines.len(),
                map.h().div_ceil(2),
                "{variant}: filas de render"
            );
            for line in lines {
                assert_eq!(visible_width(line), map.w(), "{variant}: ancho visible");
            }
        }
    }

    #[test]
    fn ansi_no_cuenta_escapes_como_ancho() {
        let colored = render_ansi(logo::mark(), ColorMode::Truecolor);
        for line in colored.lines() {
            assert!(visible_width(line) <= logo::mark().w());
        }
    }

    #[test]
    fn plain_no_tiene_escapes() {
        let plain = render_plain(logo::compact());
        assert!(!plain.contains('\x1b'));
    }

    #[test]
    fn visible_width_basico() {
        assert_eq!(visible_width("\x1b[38;2;1;2;3m▀\x1b[0m"), 1);
        assert_eq!(visible_width("abc"), 3);
    }
}
