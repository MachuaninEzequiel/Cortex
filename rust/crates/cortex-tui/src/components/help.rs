//! Overlay de ayuda (spec §12): derivada del KeyMap, nunca texto
//! hardcodeado por pantalla. Se dibuja al final (última capa).

use crate::components::panel::draw_panel;
use crate::keymap::full_help;
use crate::theme::Theme;
use ratatui::layout::Rect;
use ratatui::prelude::{Line, Span};
use ratatui::widgets::Paragraph;
use ratatui::Frame;

/// Dibuja el modal de ayuda sobre toda el área de la pantalla.
pub fn render_help(f: &mut Frame<'_>, area: Rect, theme: &Theme, lang: &'static str) {
    let inner = draw_panel(
        area,
        if lang == "en" { "HELP" } else { "AYUDA" },
        true,
        theme,
        f.buffer_mut(),
    );
    let mut lines = vec![Line::styled(
        if lang == "en" {
            "Keyboard map"
        } else {
            "Mapa de teclas"
        },
        theme.title(),
    )];
    for (k, desc) in full_help(lang) {
        lines.push(Line::from(vec![
            Span::styled(format!("{k:<12}"), theme.shortcut_key()),
            Span::styled(desc, theme.shortcut_label()),
        ]));
    }
    lines.push(Line::from(""));
    lines.push(Line::styled(
        if lang == "en" {
            "Esc closes help."
        } else {
            "Esc cierra la ayuda."
        },
        theme.muted(),
    ));
    f.render_widget(Paragraph::new(lines), inner);
}
