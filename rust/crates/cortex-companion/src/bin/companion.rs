//! Binario `cortex-companion` (B3): arranca la app, muestra el estado y
//! procesa input mouse-first/teclado. El render ratatui real llega en B4;
//! acá está el ciclo mínimo estado/acciones con snapshot no-TTY (B1/B9).

use std::io::{IsTerminal, Write};
use std::path::PathBuf;

use crossterm::event::{self, DisableMouseCapture, EnableMouseCapture};
use crossterm::{execute, terminal};

use cortex_companion::app::{self, AppState, Effect};
use cortex_companion::{Screen, UiRequest};

fn main() {
    let root = parse_args();
    let be = match cortex_companion::engine::InProcessBackend::open(&root) {
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

    // TTY: loop mínimo hasta que el usuario pida salir (q / Ctrl+C). El render
    // ratatui real llega en B4; aquí solo el ciclo estado → acciones.
    if terminal::enable_raw_mode().is_err() {
        eprintln!("no se pudo entrar en raw mode");
        return;
    }
    let _ = execute!(std::io::stdout(), EnableMouseCapture);
    let mut done = false;
    while !done {
        print!(
            "Pantalla: {} — project: {} (q para salir)\r",
            app::screen_label(st.screen),
            be.root.display()
        );
        let _ = std::io::stdout().flush();

        match event::read() {
            Ok(ev) => {
                if let Some(action) = app::translate_event(&ev) {
                    match app::update(&mut st, action) {
                        Some(Effect::RunCommand { .. }) => {
                            // B5: enrutar a lectura o guarded.
                        }
                        None => {}
                    }
                }
            }
            Err(_) => break,
        }
        if st.quit {
            done = true;
        }
    }
    let _ = execute!(std::io::stdout(), DisableMouseCapture);
    let _ = terminal::disable_raw_mode();
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
