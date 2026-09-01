//! Captura headless ANSI truecolor de las pantallas (dev): vuelca el buffer
//! EXACTO del render (símbolos + estilos) a stdout. Es la materia prima de
//! `assets/shots/make_shots.py` para regenerar las imágenes del README con
//! el diseño vigente, sin terminal real y determinista.
//!
//! ```bash
//! cargo run -p cortex-tui --example capture -- splash [--width 100] [--height 30]
//! cargo run -p cortex-tui --example capture -- home
//! cargo run -p cortex-tui --example capture -- sessions --project-root DIR [--select N]
//! cargo run -p cortex-tui --example capture -- actions --project-root DIR [--confirm N] [--select N]
//! ```

use cortex_app::session::service::SessionService;
use cortex_app::session::SessionStorage;
use cortex_tui::app::{update as reducer, Action, AppState};
use ratatui::backend::TestBackend;
use ratatui::buffer::Buffer;
use ratatui::prelude::{Color, Modifier, Rect};
use ratatui::{Terminal, TerminalOptions, Viewport};

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let screen = args.first().map(String::as_str).unwrap_or("splash");
    let (mut w, mut h) = (100u16, 30u16);
    let mut project_root: Option<String> = None;
    let mut select = 0usize;
    let mut confirm: Option<usize> = None;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--width" => {
                w = args[i + 1].parse().expect("--width");
                i += 1;
            }
            "--height" => {
                h = args[i + 1].parse().expect("--height");
                i += 1;
            }
            "--project-root" => {
                project_root = Some(args[i + 1].clone());
                i += 1;
            }
            "--select" => {
                select = args[i + 1].parse().expect("--select");
                i += 1;
            }
            "--confirm" => {
                confirm = Some(args[i + 1].parse().expect("--confirm"));
                i += 1;
            }
            _ => {}
        }
        i += 1;
    }

    let backend = TestBackend::new(w, h);
    let mut terminal = Terminal::with_options(
        backend,
        TerminalOptions {
            viewport: Viewport::Fixed(Rect::new(0, 0, w, h)),
        },
    )
    .unwrap();

    match screen {
        "home" => {
            // Home REAL: snapshot con datos del project-root (o cwd); sin
            // project-root explícito cae en el estado demo.
            let root = project_root
                .map(std::path::PathBuf::from)
                .unwrap_or_else(|| std::env::current_dir().unwrap());
            let storage = SessionStorage::new(root.join(".cortex").join("sessions"));
            let service = SessionService::new(storage, &root);
            let ctx = cortex_actions::context::ActionContext::from_project_root(Some(&root));
            let state = cortex_tui::home::snapshot(&ctx, Some(&service));
            terminal
                .draw(|f| cortex_tui::home::render(f, &state))
                .unwrap();
        }
        "sessions" => {
            let root = project_root
                .map(std::path::PathBuf::from)
                .unwrap_or_else(|| std::env::current_dir().unwrap());
            let storage = SessionStorage::new(root.join(".cortex").join("sessions"));
            let service = SessionService::new(storage, &root);
            let mut state = AppState::new("es", (w, h));
            match cortex_tui::sessions::SessionsScreenData::from_service(&service, None) {
                Ok(d) => reducer(&mut state, Action::SessionsLoaded(d)),
                Err(e) => reducer(&mut state, Action::SessionsFailed(e)),
            };
            for _ in 0..select {
                reducer(&mut state, Action::MoveDown);
            }
            terminal
                .draw(|f| cortex_tui::sessions::render(f, &state))
                .unwrap();
        }
        "actions" => {
            let root = project_root.map(std::path::PathBuf::from);
            let ctx = cortex_tui::actions::context(root.as_deref());
            let mut state = AppState::for_actions("es", (w, h));
            match cortex_tui::actions::propose(&ctx, false) {
                Ok(d) => reducer(&mut state, Action::ActionsLoaded(d)),
                Err(e) => reducer(&mut state, Action::ActionsFailed(e)),
            };
            for _ in 0..select {
                reducer(&mut state, Action::MoveDown);
            }
            if let Some(idx) = confirm {
                reducer(&mut state, Action::ConfirmAction { index: idx });
            }
            terminal
                .draw(|f| cortex_tui::actions::render(f, &state))
                .unwrap();
        }
        // splash (default): experiencia ideal con color real.
        _ => {
            terminal
                .draw(|f| {
                    cortex_tui::splash::render(f, cortex_branding::ansi::ColorMode::Truecolor)
                })
                .unwrap();
        }
    }

    let buf = terminal.backend().buffer();
    print!("{}", dump_ansi(buf));
}

/// Serializa el buffer a ANSI truecolor (SGR 38;2/48;2 + 1 para bold).
/// Formato estable, consumido por el rasterizador del repo.
fn dump_ansi(buf: &Buffer) -> String {
    let mut out = String::with_capacity(buf.area.width as usize * buf.area.height as usize * 16);
    for y in 0..buf.area.height {
        out.push_str("\x1b[0m");
        let mut prev: Option<(Color, Color, bool)> = None;
        for x in 0..buf.area.width {
            let cell = &buf[(x, y)];
            let style = cell.style();
            let fg = style.fg.unwrap_or(Color::Reset);
            let bg = style.bg.unwrap_or(Color::Reset);
            let bold = style.add_modifier.contains(Modifier::BOLD);
            let cur = (fg, bg, bold);
            if prev != Some(cur) {
                out.push_str("\x1b[0m");
                if bold {
                    out.push_str("\x1b[1m");
                }
                fg_sgr(fg, &mut out);
                bg_sgr(bg, &mut out);
                prev = Some(cur);
            }
            out.push_str(cell.symbol());
        }
        out.push_str("\x1b[0m\n");
    }
    out
}

fn fg_sgr(c: Color, out: &mut String) {
    if let Color::Rgb(r, g, b) = c {
        out.push_str(&format!("\x1b[38;2;{r};{g};{b}m"));
    }
}

fn bg_sgr(c: Color, out: &mut String) {
    if let Color::Rgb(r, g, b) = c {
        out.push_str(&format!("\x1b[48;2;{r};{g};{b}m"));
    }
}
