//! Binario `cortex-companion` (B4/B5): render de Home y Menu con ratatui +
//! crossterm, mouse-first (raw mode + mouse capture). El snapshot no-TTY de
//! B1/B9 se conserva. B5 añade el enrutado del efecto `RunCommand` del Menu:
//! lecturas directas al backend in-process; mutantes → modal de aprobación
//! (`run_guarded`, B2) — nunca ejecución directa.

#![forbid(unsafe_code)]

use std::io::IsTerminal;
use std::path::PathBuf;

use crossterm::event::{
    self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode, KeyEvent, KeyModifiers,
    MouseButton, MouseEventKind,
};
use crossterm::{execute, terminal};
use ratatui::backend::CrosstermBackend;
use ratatui::layout::{Position, Rect};
use ratatui::prelude::{Color, Line, Style};
use ratatui::text::Span;
use ratatui::widgets::{Block, Borders, Paragraph};
use ratatui::Terminal;

use cortex_companion::app::{self, AppState, Effect};
use cortex_companion::approval::{run_guarded, ActionLog, ApprovalRequest, ApprovalUi};
use cortex_companion::engine::{Backend, InProcessBackend};
use cortex_companion::menu::{self, MenuOutput};
use cortex_companion::screens::home::{home_areas, render_home, BrandAssets, HomeData};
use cortex_companion::screens::menu_screen::{menu_areas, render_menu};
use cortex_companion::{Screen, UiRequest};

type Term = Terminal<CrosstermBackend<std::io::Stdout>>;

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
        // Draw según pantalla (los renders son puros; la I/O la hace el runtime).
        let _ = terminal.draw(|f| match st.screen {
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
            other => {
                let label = app::screen_label(other);
                f.render_widget(
                    Paragraph::new(Line::from(Span::styled(
                        format!("Pantalla {label} — próxima task (B6+)"),
                        Style::default().fg(Color::DarkGray),
                    ))),
                    f.area(),
                );
            }
        });

        match event::read() {
            Ok(ev) => {
                if let Some(action) = app::translate_event(&ev) {
                    if let Some(fx) = app::update(&mut st, action) {
                        apply_effect(&mut terminal, &be, &mut st, fx);
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

/// Aplica los efectos del reducer (v1: `RunCommand` del Menu, B5).
///
/// - **Direct** → ejecuta `menu_run` in-process y guarda el resultado en el
///   panel de salida del Menu.
/// - **Guarded** → modal de aprobación + `run_guarded` (B2); la salida se
///   captura del cierre aprobado. Denegar no es error: la UI lo muestra.
fn apply_effect(term: &mut Term, be: &InProcessBackend, st: &mut AppState, fx: Effect) {
    match fx {
        Effect::RunCommand { family, args } => {
            let title = menu::entry_for(family, &args)
                .map(|e| e.title.to_string())
                .unwrap_or_else(|| family.to_string());
            if menu::command_is_guarded(family, &args) {
                let req = ApprovalRequest {
                    title: format!("Ejecutar «{title}»"),
                    effect: format!("cortex {family} {}", args.join(" "))
                        .trim_end()
                        .to_string(),
                    audit_key: format!("menu.{family}"),
                };
                let log = ActionLog::new(&be.action_log_dir());
                let mut ui = SimpleModalUi { term };
                let mut run_out: Option<String> = None;
                let result = run_guarded(&mut ui, &log, &req, || {
                    let out = be.menu_run(family, &args)?;
                    run_out = Some(out);
                    Ok(())
                });
                st.menu_output = Some(match (result, run_out) {
                    (Ok(()), Some(s)) => MenuOutput::ok(s),
                    (Ok(()), None) => {
                        MenuOutput::ok("aprobado y ejecutado (sin salida)".to_string())
                    }
                    (Err(e), _) => MenuOutput::err(e),
                });
            } else {
                st.menu_output = Some(match be.menu_run(family, &args) {
                    Ok(s) => MenuOutput::ok(s),
                    Err(e) => MenuOutput::err(e),
                });
            }
        }
    }
}

/// Modal de aprobación bloqueante mínimo (B5; B6 lo integra a la máquina de
/// estados). Dibuja el pedido y espera un clic en [Aprobar]/[Denegar] o
/// Esc/q/Ctrl+C (⇒ denegar). `ask` NO toca el dominio: solo decide.
struct SimpleModalUi<'a> {
    term: &'a mut Term,
}

const MODAL_RECT: Rect = Rect::new(10, 8, 60, 7);
const APROBAR_RECT: Rect = Rect::new(22, 12, 14, 2);
const DENEGAR_RECT: Rect = Rect::new(44, 12, 14, 2);

impl ApprovalUi for SimpleModalUi<'_> {
    fn ask(&mut self, req: &ApprovalRequest) -> bool {
        loop {
            let req = req.clone();
            let _ = self.term.draw(|f| {
                let title = Span::styled(req.title.clone(), Style::default().fg(Color::Yellow));
                let effect = Span::styled(req.effect.clone(), Style::default().fg(Color::White));
                let effect_display = effect_content(effect);
                f.render_widget(
                    Paragraph::new(vec![Line::from(effect_display)])
                        .block(Block::default().borders(Borders::ALL).title(title)),
                    MODAL_RECT,
                );
                f.render_widget(
                    Paragraph::new(Line::from(Span::styled(
                        "[ Aprobar ]",
                        Style::default()
                            .fg(Color::Green)
                            .add_modifier(ratatui::style::Modifier::BOLD),
                    ))),
                    APROBAR_RECT,
                );
                f.render_widget(
                    Paragraph::new(Line::from(Span::styled(
                        "[ Denegar ]",
                        Style::default().fg(Color::Red),
                    ))),
                    DENEGAR_RECT,
                );
                f.render_widget(
                    Paragraph::new(Line::from(Span::styled(
                        "clic o Esc/q para decidir",
                        Style::default().fg(Color::DarkGray),
                    ))),
                    Rect::new(MODAL_RECT.x + 2, MODAL_RECT.y + 5, MODAL_RECT.width - 4, 1),
                );
            });

            match event::read() {
                Ok(Event::Mouse(m))
                    if matches!(m.kind, MouseEventKind::Down(MouseButton::Left)) =>
                {
                    let p = Position::new(m.column, m.row);
                    if APROBAR_RECT.contains(p) {
                        return true;
                    }
                    if DENEGAR_RECT.contains(p) {
                        return false;
                    }
                }
                Ok(Event::Key(k)) if matches!(k.code, KeyCode::Esc) => return false,
                Ok(Event::Key(KeyEvent {
                    code: KeyCode::Char('q'),
                    ..
                })) => return false,
                Ok(Event::Key(KeyEvent {
                    code: KeyCode::Char('c'),
                    modifiers,
                    ..
                })) if modifiers.contains(KeyModifiers::CONTROL) => return false,
                Err(_) => return false,
                _ => {}
            }
        }
    }
}

/// Recorta el efecto a la caja del modal (largo variable, sin_break natural).
fn effect_content(effect: Span<'static>) -> Span<'static> {
    let content = effect.content.to_string();
    let max = (MODAL_RECT.width.saturating_sub(4)) as usize;
    if content.chars().count() > max {
        let cut: String = content.chars().take(max - 1).collect();
        Span::styled(format!("{cut}…"), effect.style)
    } else {
        effect
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
