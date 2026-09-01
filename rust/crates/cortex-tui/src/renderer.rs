//! Conversión píxeles lógicos → celdas ratatui (prompt-logo.md §10-12).
//!
//! Un `PixelMap` se pinta con half-blocks: cada celda de terminal representa
//! dos píxeles verticales (`▀` con fg=superior y bg=inferior). Celdas
//! transparentes usan fondo `Reset`: jamás se pinta el fondo del usuario.

use cortex_branding::ansi::ColorMode;
use cortex_branding::logo::LogoVariant;
use cortex_branding::palette::{self, Ansi16, Rgb};
use cortex_branding::pixels::{PixelKind, PixelMap};
use ratatui::prelude::{Buffer, Color, Rect};

/// Widget reutilizable de ratatui que renderiza una variante del isotipo
/// centrado en el área recibida (prompt §12, §19).
#[derive(Clone, Copy, Debug)]
pub struct CortexLogo {
    variant: LogoVariant,
    mode: ColorMode,
}

impl CortexLogo {
    pub fn new(variant: LogoVariant) -> Self {
        Self {
            variant,
            mode: ColorMode::Truecolor,
        }
    }

    /// Modo de color (para terminales limitadas o tests).
    pub fn with_mode(mut self, mode: ColorMode) -> Self {
        self.mode = mode;
        self
    }
}

impl ratatui::widgets::Widget for CortexLogo {
    fn render(self, area: Rect, buf: &mut Buffer) {
        render_pixel_map(self.variant.pixel_map(), self.mode, area, buf);
    }
}

/// Renderiza un `PixelMap` centrado dentro de `area` (recortado si no entra),
/// usando el gradiente menta del isotipo (`gradient::color_for`).
pub fn render_pixel_map(map: &PixelMap, mode: ColorMode, area: Rect, buf: &mut Buffer) {
    render_pixel_map_with(map, mode, area, buf, |kind, y| {
        cortex_branding::gradient::color_for(kind, y, map.h())
    });
}

/// Como [`render_pixel_map`] pero con función de color propia (p. ej. la
/// paleta fría del wordmark, que NO es el gradiente menta del isotipo).
pub fn render_pixel_map_with(
    map: &PixelMap,
    mode: ColorMode,
    area: Rect,
    buf: &mut Buffer,
    color_fn: impl Fn(PixelKind, usize) -> Option<Rgb>,
) {
    let cols = (map.w() as u16).min(area.width);
    let rows = (map.h().div_ceil(2) as u16).min(area.height);
    if cols == 0 || rows == 0 {
        return;
    }
    let x0 = area.x + (area.width - cols) / 2;
    let y0 = area.y + (area.height - rows) / 2;
    for cy in 0..rows {
        for cx in 0..cols {
            let (mx, my) = (cx as usize, cy as usize * 2);
            let top = map.get(mx, my);
            let bottom = if my + 1 < map.h() {
                map.get(mx, my + 1)
            } else {
                PixelKind::Transparent // altura impar: última fila sin par
            };
            let Some(cell) = buf.cell_mut((x0 + cx, y0 + cy)) else {
                continue;
            };
            match (top, bottom) {
                (PixelKind::Transparent, PixelKind::Transparent) => {
                    cell.set_symbol(" ");
                    cell.set_fg(Color::Reset);
                    cell.set_bg(Color::Reset);
                }
                (top, bottom) => {
                    let c_top = color_fn(top, my);
                    let c_bottom = color_fn(bottom, my + 1);
                    match (c_top, c_bottom) {
                        (None, None) => {
                            cell.set_symbol(" ");
                            cell.set_fg(Color::Reset);
                            cell.set_bg(Color::Reset);
                        }
                        (Some(t), None) => {
                            cell.set_symbol("▀");
                            cell.set_fg(to_ratatui(t, mode));
                            cell.set_bg(Color::Reset);
                        }
                        (None, Some(b)) => {
                            cell.set_symbol("▄");
                            cell.set_fg(to_ratatui(b, mode));
                            cell.set_bg(Color::Reset);
                        }
                        (Some(t), Some(b)) if t == b => {
                            cell.set_symbol("█");
                            cell.set_fg(to_ratatui(t, mode));
                            cell.set_bg(Color::Reset);
                        }
                        (Some(t), Some(b)) => {
                            cell.set_symbol("▀");
                            cell.set_fg(to_ratatui(t, mode));
                            cell.set_bg(to_ratatui(b, mode));
                        }
                    }
                }
            }
        }
    }
}

/// Mapea un color de la paleta al `Color` de ratatui según el modo.
pub fn to_ratatui(c: Rgb, mode: ColorMode) -> Color {
    match mode {
        ColorMode::Truecolor => Color::Rgb(c.0, c.1, c.2),
        ColorMode::Ansi16 => match palette::fallback(c) {
            Ansi16::DarkGray => Color::DarkGray,
            Ansi16::LightCyan => Color::LightCyan,
            Ansi16::Cyan => Color::Cyan,
            Ansi16::Blue => Color::Blue,
            Ansi16::White => Color::White,
            Ansi16::Green => Color::Green,
            Ansi16::Yellow => Color::Yellow,
            Ansi16::Red => Color::Red,
        },
        ColorMode::Plain => Color::Reset,
    }
}
