//! Binario `cortex-companion` (B4/B5/B6): render de Home, Menu, Sessions y
//! Actions con ratatui + crossterm, mouse-first (raw mode + mouse capture).
//! El snapshot no-TTY de B1/B9 se conserva. B6 integra el modal de
//! aprobación a la máquina de estados: los clicks se resuelven con
//! `hit_test`, el reducer abre `pending`, y `effects::apply` ejecuta SOLO
//! lo aprobado (`run_guarded`, B2) — sin loops bloqueantes.

#![forbid(unsafe_code)]

use std::io::IsTerminal;
use std::path::PathBuf;

use crossterm::event::{self, DisableMouseCapture, EnableMouseCapture};
use crossterm::{execute, terminal};
use ratatui::backend::CrosstermBackend;
use ratatui::prelude::{Color, Line, Style};
use ratatui::text::Span;
use ratatui::widgets::Paragraph;
use ratatui::Terminal;

use cortex_companion::app::{self, AppAction, AppState};
use cortex_companion::approval::ActionLog;
use cortex_companion::effects;
use cortex_companion::engine::{Backend, InProcessBackend};
use cortex_companion::screens::home::{home_areas, render_home, BrandAssets, HomeData};
use cortex_companion::screens::menu_screen::{menu_areas, render_menu};
use cortex_companion::screens::sessions_screen::{render_sessions, sessions_areas};
use cortex_companion::screens::{actions_areas, render_actions, render_modal};
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
    let log = ActionLog::new(&be.action_log_dir());

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
        // Refrescar datos de Sessions/Actions antes de dibujar (preservando
        // selección y resultado, que son estado del usuario, no del backend).
        match st.screen {
            Screen::Sessions => {
                let sel = st.sessions.selected;
                let outcome = st.sessions.outcome.take();
                st.sessions = sessions_data(&be, sel, outcome);
            }
            Screen::Actions => {
                let outcome = st.actions.outcome.take();
                st.actions = actions_data(&be, outcome);
            }
            _ => {}
        }

        let _ = terminal.draw(|f| {
            match st.screen {
                Screen::Home => {
                    let data = home_data(&be);
                    let mut areas = home_areas(f.area());
                    areas.hovered_mouse = st.mouse;
                    let _info = render_home(f, f.area(), &data, &BrandAssets::load(), &mut areas);
                }
                Screen::Menu => {
                    let mut areas = menu_areas(f.area());
                    areas.hover_mouse = st.mouse;
                    let _info = render_menu(
                        f,
                        f.area(),
                        st.menu_output.as_ref(),
                        st.scroll_offset,
                        &mut areas,
                    );
                }
                Screen::Sessions => {
                    let mut areas = sessions_areas(f.area());
                    areas.hover_mouse = st.mouse;
                    let _info =
                        render_sessions(f, f.area(), &st.sessions, st.scroll_offset, &mut areas);
                }
                Screen::Actions => {
                    let mut areas = actions_areas(f.area());
                    areas.hover_mouse = st.mouse;
                    let _info =
                        render_actions(f, f.area(), &st.actions, st.scroll_offset, &mut areas);
                }
                other => {
                    let label = app::screen_label(other);
                    f.render_widget(
                        Paragraph::new(Line::from(Span::styled(
                            format!("Pantalla {label} — próxima task (B7+)"),
                            Style::default().fg(Color::DarkGray),
                        ))),
                        f.area(),
                    );
                }
            }
            // Modal como superficie de la máquina de estados (B6): se pinta
            // encima de lo demás mientras `pending` está abierto.
            if let Some(p) = st.pending.as_ref() {
                render_modal(f, &p.req);
            }
        });

        match event::read() {
            Ok(ev) => {
                if let Some(action) = app::translate_event(&ev) {
                    // B6: los clicks se resuelven contra las áreas de la
                    // pantalla actual (hit-test puro); un Click sin área queda
                    // no-op en el reducer.
                    let action = match action {
                        AppAction::Click { x, y } => {
                            app::hit_test(&st, x, y).unwrap_or(AppAction::Click { x, y })
                        }
                        other => other,
                    };
                    if let Some(fx) = app::update(&mut st, action) {
                        effects::apply(&be, &log, &mut st, fx);
                    }
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

/// Refresca la lista de sesiones preservando selección y resultado (son
/// estado del usuario, no del backend). El detalle se recarga para la fila
/// seleccionada (misma regla que el panel muestra).
fn sessions_data(
    be: &InProcessBackend,
    selected: Option<usize>,
    outcome: Option<cortex_companion::app::OutcomeLine>,
) -> cortex_companion::app::SessionsData {
    let mut data = cortex_companion::app::SessionsData {
        outcome,
        ..Default::default()
    };
    match be.session_list() {
        Ok(v) => data.sessions = v,
        Err(e) => data.error = Some(e),
    }
    data.selected = selected.filter(|i| *i < data.sessions.len());
    if let Some(i) = data.selected {
        let id = data.sessions[i].id.clone();
        data.detail = be.session_detail(&id).ok().map(|l| (id, l));
    }
    data
}

/// Refresca las propuestas del motor preservando el resultado visible.
fn actions_data(
    be: &InProcessBackend,
    outcome: Option<cortex_companion::app::OutcomeLine>,
) -> cortex_companion::app::ActionsData {
    match be.next_actions() {
        Ok(proposals) => cortex_companion::app::ActionsData {
            proposals,
            outcome,
            error: None,
        },
        Err(e) => cortex_companion::app::ActionsData {
            proposals: Vec::new(),
            outcome,
            error: Some(e),
        },
    }
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
