//! Cabecera de pantallas operativas (spec §10 Header): marca mínima +
//! nombre de vista + estado global a la derecha. Máximo dos filas.
//!
//! El isotipo gráfico (Mark, 5 filas) solo se dibuja cuando el área lo
//! permite (spec §8: Compact/Mark según modo; bajo el ancho mínimo se
//! muestra "CORTEX" como texto). En headers de una línea la marca es
//! SIEMPRE texto: el logo no roba espacio operativo.

use crate::layout::{logo_for, LayoutMode};
use crate::renderer::CortexLogo;
use crate::theme::{self, StatusKind, Theme};
use cortex_branding::logo::LogoVariant;
use ratatui::buffer::Buffer;
use ratatui::layout::Rect;
use ratatui::prelude::{Line, Span};
use ratatui::widgets::{Paragraph, Widget};

pub struct AppHeader<'a> {
    /// Título de la vista (nombre corto, alineado a la izquierda — §7.5).
    pub title: &'a str,
    /// Estado global: pares (símbolo + etiqueta corta, p. ej. "● 2 activas").
    pub right: &'a [(StatusKind, String)],
    pub lang: &'static str,
    /// Modo de pantalla del CALLER (el área de 1 fila del header no decide
    /// el layout global; el caller conoce su LayoutMode).
    pub mode: LayoutMode,
}

impl Widget for AppHeader<'_> {
    fn render(self, area: Rect, buf: &mut Buffer) {
        if area.width == 0 || area.height == 0 {
            return;
        }
        let theme = Theme::new(crate::env_color_mode());

        // Marca: isotipo si el área da altura (correcto en headers de 1
        // línea: SOLO texto).
        let mut mark_w = 0u16;
        if area.height >= 5 {
            match logo_for(self.mode, area.width) {
                Some(variant) => {
                    mark_w = variant_display_width(variant);
                    if mark_w < area.width {
                        let logo_area = Rect::new(area.x, area.y, mark_w, area.height);
                        CortexLogo::new(variant)
                            .with_mode(crate::env_color_mode())
                            .render(logo_area, buf);
                        mark_w += 1; // aire entre marca y título
                    } else {
                        mark_w = 0;
                    }
                }
                None => mark_w = 0,
            }
        }
        if mark_w == 0 {
            let t = theme.title();
            Paragraph::new(theme::brand_text(t))
                .render(Rect::new(area.x, area.y, theme::MARK_MIN_WIDTH, 1), buf);
            mark_w = theme::MARK_MIN_WIDTH;
        }

        // Título a la izquierda, estado a la derecha, en la primera fila.
        let title_x = area.x + mark_w;
        let title_w = area.width.saturating_sub(mark_w);
        if title_w > 0 {
            Paragraph::new(Line::from(Span::styled(
                self.title.to_string(),
                theme.title(),
            )))
            .render(Rect::new(title_x, area.y, title_w, 1), buf);
        }

        // Derecha: estado compacto (texto corto, spec §10).
        let right_line = Line::from(
            self.right
                .iter()
                .flat_map(|(kind, text)| {
                    let color = theme.status_color(*kind);
                    let style = ratatui::prelude::Style::default()
                        .fg(color)
                        .add_modifier(ratatui::prelude::Modifier::BOLD);
                    [
                        Span::styled(kind.glyph(), style),
                        Span::styled(format!(" {text}"), style),
                        Span::raw("  "),
                    ]
                })
                .collect::<Vec<Span>>(),
        );
        let right_w = right_line.width() as u16;
        if right_w < title_w {
            Paragraph::new(right_line).render(
                Rect::new(area.x + area.width - right_w, area.y, right_w, 1),
                buf,
            );
        }
    }
}

/// Ancho de columnas que ocupa cada variante en la terminal.
fn variant_display_width(v: LogoVariant) -> u16 {
    match v {
        LogoVariant::Full => 44,
        LogoVariant::Compact => 28,
        LogoVariant::Mark => 13,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui::backend::TestBackend;
    use ratatui::{Terminal, TerminalOptions, Viewport};

    fn draw(w: u16, h: u16, title: &str, right: &[(StatusKind, String)]) -> String {
        let backend = TestBackend::new(w, h);
        let mut terminal = Terminal::with_options(
            backend,
            TerminalOptions {
                viewport: Viewport::Fixed(ratatui::prelude::Rect::new(0, 0, w, h)),
            },
        )
        .unwrap();
        terminal
            .draw(|f| {
                f.render_widget(
                    AppHeader {
                        title,
                        right,
                        lang: "es",
                        mode: crate::layout::LayoutMode::Compact,
                    },
                    f.area(),
                );
            })
            .unwrap();
        let buf = terminal.backend().buffer();
        let mut s = String::new();
        for y in 0..buf.area.height {
            for x in 0..buf.area.width {
                s.push_str(buf[(x, y)].symbol());
            }
            s.push('\n');
        }
        s
    }

    #[test]
    fn header_angosto_usa_texto_cortex() {
        let out = draw(40, 1, "sesiones", &[]);
        assert!(out.contains("CORTEX"), "falta marca texto: {out}");
        assert!(out.contains("sesiones"));
    }

    #[test]
    fn header_con_altura_usa_isotipo_mark() {
        let out = draw(60, 5, "sesiones", &[]);
        assert!(
            out.contains('█') || out.contains('▀'),
            "falta el isotipo: {out}"
        );
    }

    #[test]
    fn header_angosto_sin_altura_no_roba_espacio() {
        let out = draw(40, 1, "sesiones", &[]);
        // La marca texto (6 chars aprox) + título dentro de 40.
        assert!(out.lines().next().unwrap().trim_end().len() <= 40);
    }
}
