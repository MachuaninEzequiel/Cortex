//! Barra de estado (spec §10): atajos prioritarios (tecla en azul suave,
//! descripción muted), posición de lista y mensajes efímeros con prioridad
//! semántica. Una línea delgada.

use crate::app::state::Notification;
use crate::theme::Theme;
use ratatui::buffer::Buffer;
use ratatui::layout::Rect;
use ratatui::prelude::{Line, Modifier, Span, Style};
use ratatui::widgets::Widget;

pub struct StatusBar<'a> {
    /// Pares (tecla, descripción) — 3-5 acciones prioritarias (spec §10).
    pub hints: &'a [(&'static str, &'static str)],
    /// Posición de lista larga (spec §9).
    pub position: Option<(usize, usize)>,
    /// Mensaje efímero con prioridad semántica.
    pub message: Option<&'a Notification>,
    pub theme: &'a Theme,
}

impl Widget for StatusBar<'_> {
    fn render(self, area: Rect, buf: &mut Buffer) {
        if area.width == 0 || area.height == 0 {
            return;
        }
        let mut left: Vec<Span> = Vec::new();
        for (i, (key, label)) in self.hints.iter().enumerate() {
            if i > 0 {
                left.push(Span::styled("  ", self.theme.muted()));
            }
            left.push(Span::styled(*key, self.theme.shortcut_key()));
            left.push(Span::styled(
                format!(" {label}"),
                self.theme.shortcut_label(),
            ));
        }
        if let Some((sel, total)) = self.position {
            if left.is_empty() {
                left.push(Span::styled(
                    format!("{sel}/{total}"),
                    self.theme.subtitle(),
                ));
            } else {
                left.push(Span::styled(
                    format!("  ·  {sel}/{total}"),
                    self.theme.subtitle(),
                ));
            }
        }
        // Mensaje efímero (glyph + color semántico, spec §13 Feedback).
        if let Some(n) = self.message {
            let color = self.theme.status_color(n.kind);
            let style = Style::default().fg(color).add_modifier(Modifier::BOLD);
            left.push(Span::styled("  ", self.theme.muted()));
            left.push(Span::styled(
                format!("{} {}", n.kind.glyph(), n.text),
                style,
            ));
        }
        let line = Line::from(left);
        Widget::render(line, Rect::new(area.x, area.y, area.width, 1), buf);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::theme::StatusKind;
    use cortex_branding::ansi::ColorMode;
    use ratatui::backend::TestBackend;
    use ratatui::{Terminal, TerminalOptions, Viewport};

    #[test]
    fn hints_posicion_y_mensaje_conviven() {
        let backend = TestBackend::new(60, 1);
        let mut terminal = Terminal::with_options(
            backend,
            TerminalOptions {
                viewport: Viewport::Fixed(ratatui::prelude::Rect::new(0, 0, 60, 1)),
            },
        )
        .unwrap();
        terminal
            .draw(|f| {
                let theme = Theme::new(ColorMode::Plain);
                let sb = StatusBar {
                    hints: &[("j/k", "navegar"), ("q", "salir")],
                    position: Some((3, 12)),
                    message: Some(&Notification {
                        text: "cargado".into(),
                        kind: StatusKind::Success,
                        expires_at_tick: 0,
                    }),
                    theme: &theme,
                };
                f.render_widget(sb, f.area());
            })
            .unwrap();
        let buf = terminal.backend().buffer();
        let mut s = String::new();
        for x in 0..buf.area.width {
            s.push_str(buf[(x, 0)].symbol());
        }
        assert!(s.contains("j/k"));
        assert!(s.contains("navegar"));
        assert!(s.contains("q"));
        assert!(s.contains("salir"));
        assert!(s.contains("3/12"));
        assert!(s.contains("✓"));
    }
}
