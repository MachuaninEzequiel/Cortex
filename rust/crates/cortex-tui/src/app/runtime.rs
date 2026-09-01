//! Runtime unificado de la TUI (spec §2/§6): un solo loop para todas las
//! pantallas, con historial de navegación, efectos ejecutados FUERA del
//! reducer y restauración RAII. Los loops individuales de F2
//! (sessions::run / actions::run) se consolidan acá; las pantallas solo
//! renderizan.
//!
//! Reglas:
//! - el runtime recarga el snapshot de la pantalla ACTUAL en cada tick
//!   (mismo comportamiento que el oráculo: tiempos relativos frescos);
//! - las acciones del motor se ejecutan en un thread (feedback en vivo,
//!   spinner por tick; F3 async pleno puede reemplazar el thread);
//! - el detalle de sesión se carga por efecto (`LoadSessionDetail`).

use crate::actions;
use crate::app::state::{AppState, LoadState, Screen};
use crate::app::{update as reducer, Action, Effect};
use crate::keymap::{key_to_action, KeyContext};
use crate::sessions;
use crate::terminal::{terminal_size, Tui};
use crate::theme::{StatusKind, Theme};
use crate::{home, lang, session_detail};
use cortex_actions::context::ActionContext;
use cortex_actions::models::ActionResult;
use cortex_actions::registry::Registry;
use cortex_actions::runner::Runner;
use cortex_app::session::service::SessionService;
use cortex_app::session::{SessionStatus, SessionStorage};
use ratatui::crossterm::event::{self, Event};
use ratatui::prelude::Rect;
use ratatui::Frame;
use std::path::Path;
use std::sync::mpsc::{channel, Receiver, Sender};
use std::time::Duration;

/// Tamaño del tick en reposo (4 fps, igual que el oráculo rich).
pub const TICK_MS: u64 = 250;

/// Frames del spinner de ejecución (spec §7.4: sobrio, sin Nerd Fonts).
pub const SPINNER: [&str; 10] = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];

/// Qué pantalla abrir y con qué servicios.
pub struct UiRequest<'a> {
    pub screen: Screen,
    pub project_root: Option<&'a Path>,
    /// Filtro de status de la pantalla sesiones (watch --status).
    pub status_filter: Option<SessionStatus>,
    /// Servicio inyectado por el CLI (resolución fina de WorkspaceLayout);
    /// cuando es None el runtime construye uno desde el project_root.
    pub service: Option<&'a SessionService>,
    /// Motor de búsqueda inyectado (adapter lazy del CLI sobre
    /// NativeMemory). None ⇒ la pantalla de búsqueda falla con aviso.
    pub search: Option<std::sync::Arc<dyn crate::app::search::SearchProvider>>,
}

/// El servicio puede venir del caller o construirse acá (con el root vivo).
enum ServiceRef<'a> {
    Ref(&'a SessionService),
    Owned {
        service: SessionService,
        _root: std::path::PathBuf,
    },
}

impl ServiceRef<'_> {
    fn get(&self) -> &SessionService {
        match self {
            ServiceRef::Ref(s) => s,
            ServiceRef::Owned { service, .. } => service,
        }
    }
}

fn resolve_service<'a>(req: &UiRequest<'a>) -> Result<ServiceRef<'a>, String> {
    if let Some(s) = req.service {
        return Ok(ServiceRef::Ref(s));
    }
    let root = ActionContext::from_project_root(req.project_root);
    let root = root.repo_root;
    let storage = SessionStorage::new(root.join(".cortex").join("sessions"));
    let service = SessionService::new(storage, &root);
    Ok(ServiceRef::Owned {
        service,
        _root: root,
    })
}

// ── recarga de la pantalla actual (efecto del runtime, nunca del reducer) ──

fn reload(
    state: &mut AppState,
    service: &ServiceRef<'_>,
    ctx: &ActionContext,
    status_filter: Option<SessionStatus>,
) {
    match state.screen {
        Screen::Home => {
            // El snapshot del Home nunca falla: los problemas parciales
            // viven en el propio estado (errores/doctor-lite).
            let h = home::snapshot(ctx, Some(service.get()));
            reducer(state, Action::HomeLoaded(h));
        }
        Screen::Sessions => {
            match sessions::SessionsScreenData::from_service(service.get(), status_filter) {
                Ok(d) => {
                    reducer(state, Action::SessionsLoaded(d));
                }
                Err(e) => {
                    reducer(state, Action::SessionsFailed(e));
                }
            }
        }
        Screen::Actions => match actions::propose(ctx, false) {
            Ok(d) => {
                reducer(state, Action::ActionsLoaded(d));
            }
            Err(e) => {
                if !matches!(&state.actions, LoadState::Failed(_)) {
                    reducer(state, Action::ActionsFailed(e));
                }
            }
        },
        Screen::SessionDetail => {} // cargado por efecto (una sola vez)
        Screen::Search => {}        // la búsqueda la dispara el efecto, no el tick
    }
}

// ── ejecución de acciones (thread; resultado → canal) ──────────────────────

struct RunnerResult {
    index: usize,
    ok: bool,
    message: String,
}

/// Resultado de una búsqueda asíncrona (thread del provider).
struct SearchResult {
    data: Result<Vec<crate::app::search::SearchHit>, String>,
}

/// Resultado del detalle de sesión (cargado en thread: incluye el diff de
/// git, que puede tardar en repos grandes).
struct DetailResult {
    data: Result<crate::session_detail::SessionDetailData, String>,
}

fn spawn_search(
    provider: std::sync::Arc<dyn crate::app::search::SearchProvider>,
    query: String,
    tx: Sender<SearchResult>,
) {
    std::thread::spawn(move || {
        let data = provider.search(&query, 8);
        let _ = tx.send(SearchResult { data });
    });
}

fn spawn_execution(ctx: ActionContext, id: String, index: usize, tx: Sender<RunnerResult>) {
    std::thread::spawn(move || {
        // El registro se reconstruye por ejecución (barato; evita compartir
        // estado mutable entre hilos).
        let registry: Registry = cortex_actions::catalog::build_default_registry(&ctx);
        let mut runner = Runner::new(&ctx.dot_cortex());
        let result = match registry.get(&id) {
            // El usuario confirmó en la TUI ⇒ approved explícito (el contrato
            // del runner valida irreversible sin approved).
            Some(action) => runner.execute(&action.arc_for_run(), false, true, "user"),
            None => ActionResult::fail("acción no encontrada"),
        };
        let _ = tx.send(RunnerResult {
            index,
            ok: result.ok,
            message: result.message,
        });
    });
}

// ── render de la pantalla activa ───────────────────────────────────────────

fn render_screen(f: &mut Frame<'_>, state: &AppState) {
    let theme = Theme::new(crate::env_color_mode());
    crate::view::draw(f, state, &theme);
}

/// Render de una pantalla a un buffer para snapshots (TestBackend).
fn draw_to_buffer(state: &AppState, w: u16, h: u16) -> Result<ratatui::buffer::Buffer, String> {
    let backend = ratatui::backend::TestBackend::new(w, h);
    let mut terminal = ratatui::Terminal::with_options(
        backend,
        ratatui::TerminalOptions {
            viewport: ratatui::Viewport::Fixed(Rect::new(0, 0, w, h)),
        },
    )
    .map_err(|e| e.to_string())?;
    terminal
        .draw(|f| render_screen(f, state))
        .map_err(|e| e.to_string())?;
    Ok(terminal.backend().buffer().clone())
}

/// Snapshot de la pantalla para consola no-interactiva (CI): texto plano
/// del mismo render (contrato T6-b).
pub fn snapshot(req: UiRequest<'_>, w: u16, h: u16) -> Result<String, String> {
    let service = resolve_service(&req)?;
    let ctx = ActionContext::from_project_root(req.project_root);
    let mut state = AppState::with_screen(req.screen, lang(), (w, h));
    reload(&mut state, &service, &ctx, req.status_filter);
    let buf = draw_to_buffer(&state, w, h)?;
    let mut lines: Vec<String> = (0..buf.area.height)
        .map(|y| {
            (0..buf.area.width)
                .map(|x| buf[(x, y)].symbol().to_string())
                .collect::<String>()
                .trim_end()
                .to_string()
        })
        .collect();
    while lines.last().is_some_and(|l| l.is_empty()) {
        lines.pop();
    }
    Ok(lines.join("\n"))
}

/// Loop interactivo de la TUI (todas las pantallas).
pub fn run(req: UiRequest<'_>) -> Result<(), String> {
    let mut tui = Tui::enter()?;
    let (w, h) = terminal_size();
    let mut state = AppState::with_screen(req.screen, lang(), (w, h));
    let service = resolve_service(&req)?;
    let ctx = ActionContext::from_project_root(req.project_root);

    let backend = ratatui::backend::CrosstermBackend::new(std::io::stdout());
    let mut terminal = ratatui::Terminal::new(backend).map_err(|e| e.to_string())?;
    let (tx, rx): (Sender<RunnerResult>, Receiver<RunnerResult>) = channel();
    let (stx, srx): (Sender<SearchResult>, Receiver<SearchResult>) = channel();
    let (dtx, drx): (Sender<DetailResult>, Receiver<DetailResult>) = channel();

    loop {
        // Spinner: el tick avanza mientras una acción está ejecutándose.
        if state.actions_front().is_some() {
            reducer(&mut state, Action::Tick);
        }
        reload(&mut state, &service, &ctx, req.status_filter);
        if let Ok(r) = rx.try_recv() {
            reducer(
                &mut state,
                Action::ActionFinished {
                    index: r.index,
                    ok: r.ok,
                    message: r.message,
                },
            );
        }
        if let Ok(r) = drx.try_recv() {
            match r.data {
                Ok(d) => {
                    reducer(&mut state, Action::SessionDetailLoaded(d));
                }
                Err(e) => {
                    reducer(&mut state, Action::SessionDetailFailed(e));
                }
            }
        }
        if let Ok(r) = srx.try_recv() {
            match r.data {
                Ok(hits) => {
                    let data = crate::app::search::SearchData {
                        query: state.search_query.clone(),
                        hits,
                    };
                    reducer(&mut state, Action::SearchLoaded(data));
                }
                Err(e) => {
                    reducer(&mut state, Action::SearchFailed(e));
                }
            }
        }
        let _ = terminal.draw(|f| render_screen(f, &state));

        let poll_ms =
            if state.actions_front().is_some() || matches!(&state.search, LoadState::Loading) {
                50
            } else {
                TICK_MS
            };
        if event::poll(Duration::from_millis(poll_ms)).unwrap_or(false) {
            if let Ok(ev) = event::read() {
                // Un solo camino evento→acción→efecto: clic y tecla son
                // indivisibles (los efectos del click corren por el mismo
                // pipeline que los del teclado).
                let action = match ev {
                    Event::Key(key) => {
                        let kctx = KeyContext {
                            in_input: state.screen == Screen::Search
                                && state.search_mode == crate::app::state::SearchMode::Input,
                            overlay: state.overlay,
                            screen: state.screen,
                        };
                        key_to_action(key, kctx)
                    }
                    Event::Mouse(m) => crate::event::mouse_to_action(m),
                    Event::Resize(rw, rh) => Some(Action::Resize { width: rw, height: rh }),
                    _ => None,
                };
                if let Some(action) = action {
                    let effect = reducer(&mut state, action);
                            match effect {
                                Effect::Quit => break,
                                Effect::Search { query } => {
                                    if let Some(provider) = &req.search {
                                        spawn_search(provider.clone(), query, stx.clone());
                                    } else {
                                        reducer(
                                            &mut state,
                                            Action::SearchFailed(
                                                "motor de búsqueda no disponible en esta sesión"
                                                    .to_string(),
                                            ),
                                        );
                                    }
                                }
                                Effect::MarkUseful { memory_id } => match &req.search {
                                    Some(provider) => match provider.mark_useful(&memory_id) {
                                        Ok(()) => {
                                            state.push_notification(
                                                if state.lang == "en" {
                                                    "marked useful"
                                                } else {
                                                    "marcada útil"
                                                },
                                                StatusKind::Success,
                                            );
                                        }
                                        Err(e) => {
                                            state.push_notification(e, StatusKind::Error);
                                        }
                                    },
                                    None => {
                                        state.push_notification(
                                            if state.lang == "en" {
                                                "search engine not available"
                                            } else {
                                                "motor de búsqueda no disponible"
                                            },
                                            StatusKind::Error,
                                        );
                                    }
                                },
                                Effect::CopyToClipboard { text } => {
                                    // OSC 52: secuencia de control que la
                                    // terminal procesa directo (funciona en
                                    // SSH; no pasa por el buffer de ratatui).
                                    use std::io::Write as _;
                                    let b64 = base64::encode(&text);
                                    let mut out = std::io::stdout();
                                    let _ = write!(out, "\x1b]52;c;{b64}\x07");
                                    let _ = out.flush();
                                    let label = if state.lang == "en" {
                                        "copied"
                                    } else {
                                        "copiado"
                                    };
                                    let short = crate::components::truncate_visual(&text, 40);
                                    state.push_notification(
                                        format!("{label}: {short}"),
                                        StatusKind::Success,
                                    );
                                }
                                Effect::RunAction { index } => {
                                    let id = match &state.actions {
                                        LoadState::Ready(d) => {
                                            d.proposals.get(index).map(|p| p.id.clone())
                                        }
                                        _ => None,
                                    };
                                    if let Some(id) = id {
                                        spawn_execution(ctx.clone(), id, index, tx.clone());
                                    }
                                }
                                Effect::LoadSessionDetail { id } => {
                                    // En thread: el diff de git no congela el
                                    // loop de la TUI (el service se clona).
                                    let svc = service.get().clone();
                                    let dtx2 = dtx.clone();
                                    std::thread::spawn(move || {
                                        let data = svc.get(&id).map(|r| {
                                            let mut d =
                                                session_detail::SessionDetailData::from_record(&r);
                                            match svc.compute_diff(&id) {
                                                Ok(diff) => d.diff_preview = diff,
                                                Err(e) => d.diff_error = Some(e),
                                            }
                                            d
                                        });
                                        let _ = dtx2.send(DetailResult { data });
                                    });
                                }
                    Effect::None => {}
                }
                let _ = terminal.draw(|f| render_screen(f, &state));
                }
            }
        }
    }
    tui.restore();
    Ok(())
}
