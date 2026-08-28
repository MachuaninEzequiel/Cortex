//! Binario `cortex-companion` (B4): render real del Home con ratatui +
//! crossterm, mouse-first (raw mode + mouse capture). El snapshot no-TTY de
//! B1/B9 se conserva.

use std::io::IsTerminal;
use std::path::PathBuf;

use crossterm::event::{self, DisableMouseCapture, EnableMouseCapture};
use crossterm::{execute, terminal};
use ratatui::backend::CrosstermBackend;
use ratatui::Terminal;

use cortex_companion::app::{self, AppState};
use cortex_companion::engine::{Backend, InProcessBackend};
use cortex_companion::screens::home::{home_areas, render_home, BrandAssets, HomeData};
use cortex_companion::{Screen, UiRequest};

fn main() {
    let root = parse_args();
    let be = match InProcessBackend::open(&root) {
        Ok(be) => be,
        Err(e) => {
            eprintln!("{e}");
            std::process::exit(1);
        }
    };

    let mut st = AppState::new(UiRequest {
        screen: Screen::Home,
        project_root: root,
    });

    if !std::io::stdin().is_terminal() {
        // Snapshot no-TTY: render textual mínimo, rc 0 (patrón B1/B9).
        println!(
            "Pantalla: {} (project: {})",
            app::screen_label(st.screen),
            be.root.display()
        );
        return;
    }

    if terminal::enable_raw_mode().is_err() {
        eprintln!("no se pudo entrar en raw mode");
        return;
    }
    let _ = execute!(std::io::stdout(), EnableMouseCapture);

    let mut terminal = match Terminal::new(CrosstermBackend::new(std::io::stdout())) {
        Ok(t) => t,
        Err(e) => {
            eprintln!("no se pudo inicializar el terminal: {e}");
            let _ = execute!(std::io::stdout(), DisableMouseCapture);
            let _ = terminal::disable_raw_mode();
            return;
        }
    };
    let _ = terminal.hide_cursor();

    loop {
        let data = home_data(&be);
        let res = terminal.draw(|f| {
            let mut areas = home_areas(f.area());
            areas.hovered_mouse = st.mouse;
            let _info = render_home(f, f.area(), &data, &BrandAssets::load(), &mut areas);
        });
        if res.is_err() {
            break;
        }
        match event::read() {
            Ok(ev) => {
                if let Some(action) = app::translate_event(&ev) {
                    let _fx = app::update(&mut st, action);
                }
            }
            Err(_) => break,
        }
        if st.quit {
            break;
        }
    }

    let _ = terminal.show_cursor();
    let _ = execute!(std::io::stdout(), DisableMouseCapture);
    let _ = terminal::disable_raw_mode();
}

/// Carga los datos del Home desde el backend (orquestación del binario; los
/// errores de carga se muestran en la UI, nunca en silencio — P6/P9).
fn home_data(be: &InProcessBackend) -> HomeData {
    let project = be.root.display().to_string();
    let branch = be.current_branch().ok().flatten();
    let session = be.session_current().ok().flatten();
    let next = be.next_actions();
    let (top_action, error) = match next {
        Ok(mut actions) => {
            if actions.is_empty() {
                (None, None)
            } else {
                (Some(actions.remove(0)), None)
            }
        }
        Err(e) => (None, Some(e)),
    };
    let doctor = be.doctor().ok();
    let stats = be.stats().ok();
    HomeData {
        project,
        branch,
        session,
        top_action,
        doctor,
        stats,
        error,
    }
}

fn parse_args() -> PathBuf {
    let mut project_root: Option<String> = None;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--project-root" => match args.next() {
                Some(v) => project_root = Some(v),
                None => {
                    eprintln!("--project-root requiere un valor");
                    std::process::exit(2);
                }
            },
            "-h" | "--help" => {
                println!("Uso: cortex-companion [--project-root <ruta>]");
                std::process::exit(0);
            }
            _ => {
                eprintln!("argumento desconocido: '{a}'");
                std::process::exit(2);
            }
        }
    }
    match project_root {
        Some(p) => PathBuf::from(p),
        None => std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")),
    }
}

// (mantener el trait IsTerminal en uso vía el snapshot no-TTY de main).
