//! Panel principal (spec §13): borde redondeado con título, idle/focus.
//! El layout INTERNO nunca se decide acá — el caller compone.

use crate::theme::Theme;
use ratatui::layout::Rect;

/// Devuelve el área interna de un panel principal en `area` (border + título
/// ya dibujados en `buf`).
pub fn draw_panel(
    area: Rect,
    title: &str,
    focused: bool,
    theme: &Theme,
    buf: &mut ratatui::buffer::Buffer,
) -> Rect {
    let block = theme.panel_block(title, focused);
    let inner = block.inner(area);
    ratatui::widgets::Widget::render(block, area, buf);
    inner
}

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui::backend::TestBackend;
    use ratatui::{Terminal, TerminalOptions, Viewport};

    #[test]
    fn panel_pinta_borde_y_deja_inner() {
        let backend = TestBackend::new(20, 5);
        let terminal = Terminal::with_options(
            backend,
            TerminalOptions {
                viewport: Viewport::Fixed(ratatui::prelude::Rect::new(0, 0, 20, 5)),
            },
        )
        .unwrap();
        let mut buf = terminal.backend().buffer().clone();
        let inner = draw_panel(
            ratatui::prelude::Rect::new(0, 0, 20, 5),
            "T",
            true,
            &Theme::new(cortex_branding::ansi::ColorMode::Plain),
            &mut buf,
        );
        assert_eq!(inner.width, 18);
        assert_eq!(inner.height, 3);
        // Borde redondeado presente.
        assert_eq!(buf[(0, 0)].symbol(), "╭");
    }
}
