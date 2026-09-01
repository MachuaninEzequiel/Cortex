//! Estado vacío (spec §13 EmptyState / §11.7): explica QUÉ falta y ofrece
//! una acción concreta. Nunca un panel vacío sin explicación.

use crate::theme::{StatusKind, Theme};
use ratatui::buffer::Buffer;
use ratatui::layout::Rect;
use ratatui::prelude::{Alignment, Line, Style};
use ratatui::widgets::{Paragraph, Widget};

pub struct EmptyState<'a> {
    pub kind: StatusKind,
    pub title: &'a str,
    pub body: &'a [&'a str],
    /// Acción concreta (p. ej. "q para salir · cortex start para abrir una").
    pub hint: Option<&'a str>,
    pub theme: &'a Theme,
}

impl Widget for EmptyState<'_> {
    fn render(self, area: Rect, buf: &mut Buffer) {
        let style_kind = Style::default()
            .fg(self.theme.status_color(self.kind))
            .add_modifier(ratatui::prelude::Modifier::BOLD);
        let title_line = Line::from(vec![
            ratatui::text::Span::styled(format!("{} ", self.kind.glyph()), style_kind),
            ratatui::text::Span::styled(self.title.to_string(), style_kind),
        ]);
        let mut lines = vec![title_line, Line::from("")];
        lines.extend(
            self.body
                .iter()
                .map(|b| Line::styled(b.to_string(), self.theme.body())),
        );
        if let Some(h) = self.hint {
            lines.push(Line::styled(h.to_string(), self.theme.muted()));
        }
        let par = Paragraph::new(lines).alignment(Alignment::Center);
        par.render(area, buf);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use cortex_branding::ansi::ColorMode;
    use ratatui::backend::TestBackend;
    use ratatui::{Terminal, TerminalOptions, Viewport};

    #[test]
    fn empty_state_explica_y_ofrece_accion() {
        let backend = TestBackend::new(60, 8);
        let mut terminal = Terminal::with_options(
            backend,
            TerminalOptions {
                viewport: Viewport::Fixed(ratatui::prelude::Rect::new(0, 0, 60, 8)),
            },
        )
        .unwrap();
        let mut out = String::new();
        terminal
            .draw(|f| {
                let theme = Theme::new(ColorMode::Plain);
                let es = EmptyState {
                    kind: StatusKind::Pending,
                    title: "(no sessions on disk)",
                    body: &["Abrí una con: cortex start"],
                    hint: Some("q salir"),
                    theme: &theme,
                };
                f.render_widget(es, f.area());
            })
            .unwrap();
        let buf = terminal.backend().buffer();
        for y in 0..buf.area.height {
            for x in 0..buf.area.width {
                out.push_str(buf[(x, y)].symbol());
            }
            out.push('\n');
        }
        assert!(out.contains("(no sessions on disk)"));
        assert!(out.contains("cortex start"));
        assert!(out.contains("q salir"));
    }
}
