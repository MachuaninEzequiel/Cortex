//! Feedback efímero dentro de la TUI (spec §13): toast/banner, nunca
//! `println!` sobre alternate screen. Los errores persisten hasta acción
//! del usuario; los éxitos expiran (ver `app::update::expire_notifications`).

pub use crate::app::state::Notification;

/// Construye la línea del mensaje con glyph + color semántico (usado por
/// la StatusBar). Centralizado para que el estilo sea único en la app.
pub fn message_line(
    n: &Notification,
    theme: &crate::theme::Theme,
) -> ratatui::prelude::Line<'static> {
    use ratatui::prelude::{Modifier, Span, Style};
    let style = Style::default()
        .fg(theme.status_color(n.kind))
        .add_modifier(Modifier::BOLD);
    ratatui::prelude::Line::from(vec![
        Span::styled(format!("{} ", n.kind.glyph()), style),
        Span::styled(n.text.clone(), style),
    ])
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::theme::{StatusKind, Theme};
    use cortex_branding::ansi::ColorMode;

    #[test]
    fn linea_lleva_glyph_y_texto() {
        let n = Notification {
            text: "listo".into(),
            kind: StatusKind::Success,
            expires_at_tick: 0,
        };
        let theme = Theme::new(ColorMode::Plain);
        let line = message_line(&n, &theme);
        let s: String = line.spans.iter().map(|s| s.content.as_ref()).collect();
        assert_eq!(s, "✓ listo");
    }
}
