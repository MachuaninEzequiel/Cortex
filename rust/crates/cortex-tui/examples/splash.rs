//! Demo responsive del splash (prompt-logo.md §43-44): redimensioná la
//! terminal y el branding cambia Full → Compact → Minimal en vivo.
//!
//! ```bash
//! cargo run -p cortex-tui --example splash
//! ```

use ratatui::backend::CrosstermBackend;
use ratatui::crossterm::event::{self, Event, KeyCode};
use ratatui::crossterm::terminal::{
    disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen,
};
use ratatui::crossterm::ExecutableCommand;
use ratatui::{Terminal, TerminalOptions, Viewport};
use std::io::stdout;

fn main() -> std::io::Result<()> {
    enable_raw_mode()?;
    stdout().execute(EnterAlternateScreen)?;
    let mut terminal = Terminal::with_options(
        CrosstermBackend::new(stdout()),
        TerminalOptions {
            viewport: Viewport::Fullscreen,
        },
    )?;

    loop {
        terminal.draw(|f| cortex_tui::splash::render(f, cortex_tui::env_color_mode()))?;
        if let Event::Key(key) = event::read()? {
            if key.kind == event::KeyEventKind::Press
                && matches!(
                    key.code,
                    KeyCode::Char('q') | KeyCode::Esc | KeyCode::Char('Q')
                )
            {
                break;
            }
        }
    }

    disable_raw_mode()?;
    stdout().execute(LeaveAlternateScreen)?;
    Ok(())
}
