//! Preview headless del Home (dev): renderiza el estado demo a un buffer
//! TestBackend 80×24 y lo vuelca como texto.
//!
//! ```bash
//! cargo run -p cortex-tui --example home_preview
//! ```

use ratatui::backend::TestBackend;
use ratatui::{Terminal, TerminalOptions, Viewport};

fn main() {
    let backend = TestBackend::new(80, 24);
    let mut terminal = Terminal::with_options(
        backend,
        TerminalOptions {
            viewport: Viewport::Fixed(ratatui::prelude::Rect::new(0, 0, 80, 24)),
        },
    )
    .unwrap();
    let state = cortex_tui::home::demo_state();
    terminal
        .draw(|f| cortex_tui::home::render(f, &state))
        .unwrap();

    let buf = terminal.backend().buffer();
    for y in 0..buf.area.height {
        let mut line = String::new();
        for x in 0..buf.area.width {
            line.push_str(buf[(x, y)].symbol());
        }
        println!("{line}");
    }
}
