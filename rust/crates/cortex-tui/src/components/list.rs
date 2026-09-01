//! Lista seleccionable (spec §13 SelectableList): ventana + barra lateral de
//! selección + conteo de posición. El CALLER estiliza las filas (incluida
//! la seleccionada con `theme.selected()`); este widget solo hace el
//! windowing determinístico y la marca de foco (`▌`, spec §7.4).

use crate::theme::Theme;
use ratatui::buffer::Buffer;
use ratatui::layout::Rect;
use ratatui::prelude::Line;
use ratatui::widgets::Widget;

/// Ítem de la lista: una o más líneas ya estilizadas por el caller.
pub struct SelectableList<'a> {
    pub items: &'a [Vec<Line<'a>>],
    pub selected: usize,
    pub offset: usize,
    pub theme: &'a Theme,
}

impl Widget for SelectableList<'_> {
    fn render(self, area: Rect, buf: &mut Buffer) {
        if area.width == 0 || area.height == 0 {
            return;
        }
        let visible = area.height as usize;
        let mut row = 0usize;
        let mut i = self.offset;
        while row < visible && i < self.items.len() {
            for line in self.items[i].iter() {
                if row >= visible {
                    break;
                }
                let y = area.y + row as u16;
                // Barra lateral de selección (spec §7.4: elegir ›/▸/▌ y usar
                // una sola en toda la app — aquí ▌).
                let is_sel = i == self.selected;
                let marker = if is_sel { "▌" } else { " " };
                let marker_style = if is_sel {
                    self.theme.shortcut_key()
                } else {
                    self.theme.muted()
                };
                buf.set_string(area.x, y, marker, marker_style);
                // El contenido va estilizado por el caller; acá solo se
                // recorta al ancho (Line::render clampea sin escribir fuera).
                let line_w = area.width.saturating_sub(1);
                Widget::render(line.clone(), Rect::new(area.x + 1, y, line_w, 1), buf);
                row += 1;
            }
            i += 1;
        }
        // Conteo de posición a la derecha cuando hay overflow (spec §9:
        // "12/84, scrollbar o ↓ 23 más").
        if self.items.len() > visible {
            let pos = format!("{}/{}", self.selected + 1, self.items.len());
            let pos_x = area.x + area.width - pos.len() as u16;
            buf.set_string(pos_x, area.y, pos, self.theme.subtitle());
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use cortex_branding::ansi::ColorMode;
    use ratatui::backend::TestBackend;
    use ratatui::{Terminal, TerminalOptions, Viewport};

    fn draw(items: usize, selected: usize, offset: usize, w: u16, h: u16) -> String {
        let backend = TestBackend::new(w, h);
        let mut terminal = Terminal::with_options(
            backend,
            TerminalOptions {
                viewport: Viewport::Fixed(ratatui::prelude::Rect::new(0, 0, w, h)),
            },
        )
        .unwrap();
        let rows: Vec<Vec<Line<'static>>> = (0..items)
            .map(|i| vec![Line::from(format!("fila {i}"))])
            .collect();
        terminal
            .draw(|f| {
                let theme = Theme::new(ColorMode::Plain);
                let list = SelectableList {
                    items: &rows,
                    selected,
                    offset,
                    theme: &theme,
                };
                f.render_widget(list, f.area());
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
    fn muestra_ventana_y_marca_seleccion() {
        let out = draw(10, 2, 0, 20, 4);
        assert!(out.contains("fila 0"));
        assert!(out.contains("fila 3"));
        assert!(!out.contains("fila 9")); // fuera de la ventana
                                          // La fila seleccionada (offset 0 → fila 2) lleva la barra ▌.
        assert!(out.lines().nth(2).unwrap().starts_with('▌'));
    }

    #[test]
    fn ventana_respeta_offset() {
        let out = draw(10, 2, 5, 20, 4);
        assert!(!out.contains("fila 0"));
        assert!(out.contains("fila 5"));
        assert!(out.contains("fila 8"));
        assert!(!out.contains("fila 9"));
    }

    #[test]
    fn posicion_visible_en_overflow() {
        let out = draw(10, 2, 0, 20, 3);
        assert!(out.contains("3/10"), "falta conteo: {out}");
    }
}
