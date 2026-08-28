//! Máquina ELM-lite de la app (G-B2a): estado + acciones semánticas +
//! reducer puro + efectos, e input mouse-first con teclado dual.
//!
//! El render NUNCA muta estado: la UI reduce `AppAction` vía `update` y solo
//! produce un `Effect` opcional que el runtime (binario) aplica. El hit-test
//! es puro: `rects` registradas + coordenadas del click ⇒ `AppAction`.

use crossterm::event::{Event, KeyCode, KeyEvent, KeyModifiers, MouseButton, MouseEventKind};
use ratatui::layout::{Position, Rect};

use crate::approval::ApprovalRequest;
use crate::engine::{ActionProposal, SessionSummary};
use crate::menu::{self, MenuOutput};
use crate::{Screen, UiRequest};

/// Rects canónicas del Home (header). B3 definió la de Sesiones y los tests
/// la usan; B4 agrega las de acciones y abrir-sesión. El hit-test (`hit_test`)
/// y el render (`home_areas`) usan las MISMAS consts ⇒ coinciden SIEMPRE.
pub const HOME_SESSIONS_BTN: Rect = Rect::new(2, 4, 18, 3);
pub const HOME_ACTIONS_BTN: Rect = Rect::new(24, 4, 18, 3);
pub const HOME_OPEN_SESSION_BTN: Rect = Rect::new(46, 4, 18, 3);
/// Botón de navegación al Menu (B5): el anti-olvido tiene entrada desde Home.
pub const HOME_MENU_BTN: Rect = Rect::new(66, 4, 12, 3);

/// Rects canónicas del Menu (B5). Compartidas por `hit_test`, `menu_areas` y
/// `render_menu` — la lista arranca abajo del header y el panel de salida en
/// el caja inferior (80x24 es la referencia del repo).
pub const MENU_LIST_LEFT: u16 = 2;
pub const MENU_LIST_TOP: u16 = 4;
pub const MENU_LIST_WIDTH: u16 = 56;
pub const MENU_LIST_HEIGHT: u16 = 16;
pub const MENU_OUTPUT_TOP: u16 = 20;
pub const MENU_OUTPUT_HEIGHT: u16 = 3;
pub const MENU_BACK_BTN: Rect = Rect::new(58, 1, 20, 3);

/// Modal de aprobación (B6): geométrica COMPARTIDA por `hit_test` (trampa de
/// foco) y `screens::render_modal` — el modal vive en la máquina de estados,
/// NO en un loop bloqueante (integración pedida en el review de B5).
pub const MODAL_RECT: Rect = Rect::new(10, 8, 60, 7);
pub const MODAL_APROBAR_RECT: Rect = Rect::new(22, 12, 14, 2);
pub const MODAL_DENEGAR_RECT: Rect = Rect::new(44, 12, 14, 2);

/// Pantalla Sessions: lista de filas (click ⇒ selección), botón [Cerrar
/// sesión] (guarded) y paneles de detalle/salida.
pub const SESSIONS_LIST_LEFT: u16 = 2;
pub const SESSIONS_LIST_TOP: u16 = 4;
pub const SESSIONS_LIST_WIDTH: u16 = 76;
pub const SESSIONS_LIST_HEIGHT: u16 = 10;
pub const SESSIONS_CLOSE_BTN: Rect = Rect::new(58, 1, 20, 2);
pub const SESSIONS_DETAIL: Rect = Rect::new(2, 15, 76, 7);
pub const SESSIONS_OUTCOME: Rect = Rect::new(2, 22, 76, 2);

/// Pantalla Actions: filas de propuestas con columna [Aprobar] por fila y
/// botón de lote auto-ok arriba. La columna es hit-test por fila visible.
pub const ACTIONS_LIST_LEFT: u16 = 2;
pub const ACTIONS_LIST_TOP: u16 = 5;
pub const ACTIONS_LIST_WIDTH: u16 = 56;
pub const ACTIONS_LIST_HEIGHT: u16 = 12;
pub const ACTIONS_APPROVE_X: u16 = 58;
pub const ACTIONS_APPROVE_W: u16 = 14;
pub const ACTIONS_BATCH_BTN: Rect = Rect::new(2, 2, 26, 2);
pub const ACTIONS_OUTCOME: Rect = Rect::new(2, 18, 76, 6);

/// Pantalla Search (B7): input con cursor, lista de hits con columna [Útil]
/// (solo filas episódicas — sin `memory_id` no hay qué puntuar, core.py:274)
/// y detalle del seleccionado. Geometría COMPARTIDA con `hit_test`.
pub const SEARCH_STATUS: Rect = Rect::new(2, 1, 76, 1);
/// Alto 2: fila de texto + fila del borde inferior (Borders::BOTTOM consume
/// una fila del rect — con alto 1 el `Paragraph` inner quedaba en 0 y la
/// query no se renderizaba; B7 fix).
pub const SEARCH_INPUT: Rect = Rect::new(2, 2, 76, 2);
pub const SEARCH_LIST_LEFT: u16 = 2;
pub const SEARCH_LIST_TOP: u16 = 4;
pub const SEARCH_LIST_WIDTH: u16 = 76;
pub const SEARCH_LIST_HEIGHT: u16 = 12;
pub const SEARCH_USEFUL_X: u16 = 58;
pub const SEARCH_USEFUL_W: u16 = 14;
pub const SEARCH_DETAIL: Rect = Rect::new(2, 17, 76, 6);

/// Acciones semánticas de la app: el input ya viene "traducido".
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AppAction {
    /// Ir a una pantalla (push navegación).
    Navigate(Screen),
    /// Click en coordenadas absolutas (resuelto por `hit_test`).
    Click {
        x: u16,
        y: u16,
    },
    /// Scroll (rueda hacia abajo/arriba).
    Scroll {
        down: bool,
    },
    /// Mouse en movimiento (para hover en widgets; el render lo lee del estado).
    MouseMoved {
        x: u16,
        y: u16,
    },
    /// Carácter tecleado (input).
    Typed(char),
    /// Tecla especial no tipográfica (Enter, Tab, F-keys…; el foco las usa en B4+).
    Key(KeyCode),
    /// Aprobar/Denegar la mutación pendiente (B6: el modal de la máquina de
    /// estados; `audit_key` debe coincidir con el `pending.req.audit_key`).
    Approve {
        audit_key: String,
    },
    Deny {
        audit_key: String,
    },
    /// Seleccionar una fila de la lista de sesiones (click ⇒ detalle).
    SelectSession {
        index: usize,
    },
    /// [Cerrar sesión] en la sesión seleccionada ⇒ modal guarded.
    CloseSession {
        session_id: String,
    },
    /// [Aprobar] de una propuesta de acción ⇒ modal guarded.
    ApproveProposal {
        id: String,
    },
    /// [Aprobar lote auto-ok]: solo propuestas reversibles de costo instant.
    ApproveBatch,
    /// Seleccionar una fila de resultados de búsqueda (click ⇒ detalle).
    SelectHit {
        index: usize,
    },
    /// [Útil] de un hit episódico: feedback explícito directo (sin modal —
    /// es la marca de aprendizaje del usuario sobre su propio índice, misma
    /// semántica que la `y` de la TUI; spec 14 §3).
    MarkUseful {
        memory_id: String,
    },
    /// Ejecutar un comando del Menu (B5: lecturas directas; mutantes ⇒ modal).
    RunCommand {
        family: &'static str,
        args: Vec<String>,
    },
    /// Volver a la pantalla previa de la pila.
    Back,
    /// Salir de la app.
    Quit,
}

/// Efecto declarado por el reducer para que el runtime lo aplique. El reducer
/// es puro: no toca terminal, procesos ni dominio.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Effect {
    /// Ejecutar un comando de lectura del catálogo (B5; guarded ya NO llega
    /// acá: abre el modal como estado, spec §5).
    RunCommand {
        family: &'static str,
        args: Vec<String>,
    },
    /// Buscar con la query (B7): el runtime llama `Backend::search` (misma
    /// pipeline híbrida del CLI, top-k 5) y refresca los hits.
    Search { query: String },
    /// Persistir el feedback explícito positivo de un hit (B7): escritor
    /// formato-oráculo (`feedback.rs`), idempotente por hit.
    MarkUseful { memory_id: String },
    /// Resolver la aprobación pendiente: el runtime (`effects::apply`)
    /// ejecuta `run_guarded` con la decisión guardada en `pending`.
    ResolveApproval,
}

/// Qué se va a ejecutar si el usuario aprueba el modal (datos puros; la
/// ejecución la hace el runtime en `effects::apply`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ApprovalTarget {
    CloseSession {
        session_id: String,
    },
    ApproveAction {
        id: String,
    },
    ApproveBatch {
        ids: Vec<String>,
    },
    RunMenu {
        family: &'static str,
        args: Vec<String>,
    },
}

/// Aprobación pendiente (superficie de la máquina de estados): pedido, qué
/// ejecuta si se aprueba, y la decisión del usuario una vez que clickea.
#[derive(Debug, Clone)]
pub struct PendingApproval {
    pub req: ApprovalRequest,
    pub target: ApprovalTarget,
    pub decision: Option<bool>,
}

/// (mensaje, es_error) — línea de resultado de una mutación resuelta.
pub type OutcomeLine = (String, bool);

/// Datos de la pantalla Sessions (los refresca el runtime antes de cada
/// draw; los tests los setean directo).
#[derive(Debug, Clone, Default)]
pub struct SessionsData {
    pub sessions: Vec<SessionSummary>,
    pub selected: Option<usize>,
    /// (id de la sesión, líneas del detalle con checkpoints/tasks).
    pub detail: Option<(String, Vec<String>)>,
    pub outcome: Option<OutcomeLine>,
    pub error: Option<String>,
}

/// Datos de la pantalla Actions.
#[derive(Debug, Clone, Default)]
pub struct ActionsData {
    pub proposals: Vec<ActionProposal>,
    pub outcome: Option<OutcomeLine>,
    pub error: Option<String>,
}

pub use crate::screens::search_screen::SearchData;

/// IDs de propuestas aptas para el lote auto-ok: reversibles Y costo
/// instantáneo (spec 14: las que tardan o mutan irreversible piden
/// confirmación individual, siempre).
pub fn batchable_ids(state: &AppState) -> Vec<String> {
    state
        .actions
        .proposals
        .iter()
        .filter(|p| p.reversible && p.cost == "instant")
        .map(|p| p.id.clone())
        .collect()
}

/// Áreas hit-testables por pantalla. B3 sólo define la del Home; B4+ suma el
/// resto (Sessions/Actions/Menu/Search/Brain) a medida que se renderizan.
#[derive(Debug, Clone, Default)]
pub struct Areas {
    pub home_sessions_btn: Option<Rect>,
    pub home_actions_btn: Option<Rect>,
    pub home_open_session_btn: Option<Rect>,
    pub home_menu_btn: Option<Rect>,
    pub menu_back_btn: Option<Rect>,
}

/// Estado global de la app (máquina ELM-lite).
#[derive(Debug, Clone)]
pub struct AppState {
    pub screen: Screen,
    /// Pila de navegación (para `Back`).
    pub stack: Vec<Screen>,
    pub areas: Areas,
    /// Flag de salida (lo setea `Quit`/`q`).
    pub quit: bool,
    /// Offset de scroll actual (v1: preservado, consumido por pantallas B4+).
    pub scroll_offset: u16,
    /// Última posición del mouse (para hover). `None` = aún no se movió.
    pub mouse: Option<(u16, u16)>,
    /// Salida del último comando del Menu (para el panel de salida).
    pub menu_output: Option<MenuOutput>,
    /// Aprobación pendiente (modal de la máquina de estados, B6). Mientras
    /// está `Some`, la trampa de foco captura todo el input.
    pub pending: Option<PendingApproval>,
    /// Datos de Sessions/Actions (refrescados por el runtime antes de draw).
    pub sessions: SessionsData,
    pub actions: ActionsData,
    /// Datos de Search (B7): query/hits/marcas — estado del usuario, no se
    /// refresca solo; Enter dispara la búsqueda.
    pub search: SearchData,
}

impl AppState {
    pub fn new(req: UiRequest) -> Self {
        Self {
            screen: req.screen,
            stack: Vec::new(),
            areas: Areas {
                home_sessions_btn: Some(HOME_SESSIONS_BTN),
                home_actions_btn: Some(HOME_ACTIONS_BTN),
                home_open_session_btn: Some(HOME_OPEN_SESSION_BTN),
                home_menu_btn: Some(HOME_MENU_BTN),
                menu_back_btn: Some(MENU_BACK_BTN),
            },
            quit: false,
            scroll_offset: 0,
            mouse: None,
            menu_output: None,
            pending: None,
            sessions: SessionsData::default(),
            actions: ActionsData::default(),
            search: SearchData::default(),
        }
    }
}

/// Reducer puro: transforma estado + acción ⇒ (posible efecto). No hace I/O.
pub fn update(state: &mut AppState, action: AppAction) -> Option<Effect> {
    // B6 — trampa de foco del modal (spec 14 §5): mientras hay aprobación
    // pendiente, SOLO Aprobar/Denegar deciden; Esc/Back/Quit equivalen a
    // denegar (semántica del modal de B5); el resto del input se ignora.
    if state.pending.is_some() {
        let answer = match &action {
            AppAction::Approve { audit_key }
                if state
                    .pending
                    .as_ref()
                    .is_some_and(|p| &p.req.audit_key == audit_key) =>
            {
                Some(true)
            }
            AppAction::Deny { audit_key }
                if state
                    .pending
                    .as_ref()
                    .is_some_and(|p| &p.req.audit_key == audit_key) =>
            {
                Some(false)
            }
            AppAction::Back | AppAction::Quit => Some(false),
            _ => None,
        };
        if let Some(ans) = answer {
            if let Some(p) = state.pending.as_mut() {
                p.decision = Some(ans);
            }
            return Some(Effect::ResolveApproval);
        }
        return None;
    }
    match action {
        AppAction::Navigate(s) => {
            state.stack.push(state.screen);
            state.screen = s;
            None
        }
        AppAction::Back => {
            if let Some(prev) = state.stack.pop() {
                state.screen = prev;
            }
            None
        }
        AppAction::Quit => {
            state.quit = true;
            // Salir es estado, no efecto: el runtime observa `quit` tras el update.
            None
        }
        // Click ya fue resuelto por `hit_test` en una acción concreta; si llega
        // aquí suelto es porque no había área (no-op).
        AppAction::Click { .. } => None,
        // ---- B7: input de búsqueda (teclado) ----
        // `/` desde cualquier otra pantalla salta al panel (convención del
        // keymap TUI del repo); en Search, `/` es texto de la consulta.
        AppAction::Typed('/') if state.screen != Screen::Search => {
            state.stack.push(state.screen);
            state.screen = Screen::Search;
            None
        }
        AppAction::Typed(c) => {
            if state.screen == Screen::Search {
                state.search.query.push(c);
            }
            None
        }
        AppAction::Key(KeyCode::Backspace) => {
            if state.screen == Screen::Search {
                state.search.query.pop();
            }
            None
        }
        AppAction::Key(KeyCode::Enter) => {
            if state.screen != Screen::Search {
                return None;
            }
            let q = state.search.query.trim().to_string();
            if q.is_empty() {
                // Query vacía ⇒ NUNCA se llama al backend (brief Step 1).
                return None;
            }
            Some(Effect::Search { query: q })
        }
        // Scroll saturante en ambas direcciones (B3 review: up debe decrementar).
        AppAction::Scroll { down } => {
            state.scroll_offset = if down {
                state.scroll_offset.saturating_add(1)
            } else {
                state.scroll_offset.saturating_sub(1)
            };
            None
        }
        AppAction::MouseMoved { x, y } => {
            state.mouse = Some((x, y));
            None
        }
        // (Typed y Key(Backspace/Enter) se resolvieron en las ramas B7 de
        // arriba.) Otras teclas especiales (Tab, F-keys) quedan no-op hasta
        // que el foco las necesite.
        AppAction::Key(_) => None,
        // Sin modal abierto, Aprobar/Denegar sueltos no significan nada.
        AppAction::Approve { .. } | AppAction::Deny { .. } => None,
        // ---- B6: Sessions ----
        AppAction::SelectSession { index } => {
            if index < state.sessions.sessions.len() {
                state.sessions.selected = Some(index);
            }
            None
        }
        AppAction::CloseSession { session_id } => {
            state.pending = Some(PendingApproval {
                req: ApprovalRequest {
                    title: format!("Cerrar sesión {session_id}"),
                    // El modal muestra SIEMPRE el efecto exacto (spec §5):
                    // comando EJECUTABLE del CLI nativo — `cortex finish` (alias
                    // documentado de finish-session; `cortex session finish` no
                    // existe). La sesión identificada queda en el título.
                    effect: "cortex finish".to_string(),
                    audit_key: format!("session.close.{session_id}"),
                },
                target: ApprovalTarget::CloseSession { session_id },
                decision: None,
            });
            None
        }
        // ---- B6: Actions ----
        AppAction::ApproveProposal { id } => {
            // Sin propuesta (fila fantasma): no-op.
            let p = state.actions.proposals.iter().find(|p| p.id == id)?;
            let (title, effect) = (p.title.clone(), p.effect.clone());
            state.pending = Some(PendingApproval {
                req: ApprovalRequest {
                    title: format!("Aprobar «{title}»"),
                    effect,
                    audit_key: id.clone(),
                },
                target: ApprovalTarget::ApproveAction { id },
                decision: None,
            });
            None
        }
        AppAction::ApproveBatch => {
            let ids = batchable_ids(state);
            if ids.is_empty() {
                return None;
            }
            state.pending = Some(PendingApproval {
                req: ApprovalRequest {
                    title: format!("Aprobar lote auto-ok ({})", ids.len()),
                    effect: format!("acciones reversibles de costo instant: {}", ids.join(", ")),
                    audit_key: "lote.auto-ok".to_string(),
                },
                target: ApprovalTarget::ApproveBatch { ids },
                decision: None,
            });
            None
        }
        // ---- B7: Search ----
        AppAction::SelectHit { index } => {
            if index < state.search.hits.len() {
                state.search.selected = Some(index);
            }
            None
        }
        AppAction::MarkUseful { memory_id } => Some(Effect::MarkUseful { memory_id }),
        AppAction::RunCommand { family, args } => {
            // B6: las mutantes del menú pasan por el modal de la máquina de
            // estados (ya no hay loop bloqueante en el runtime).
            if menu::command_is_guarded(family, &args) {
                let title = menu::entry_for(family, &args)
                    .map(|e| e.title.to_string())
                    .unwrap_or_else(|| family.to_string());
                state.pending = Some(PendingApproval {
                    req: ApprovalRequest {
                        title: format!("Ejecutar «{title}»"),
                        effect: format!("cortex {family} {}", args.join(" "))
                            .trim_end()
                            .to_string(),
                        audit_key: format!("menu.{family}"),
                    },
                    target: ApprovalTarget::RunMenu { family, args },
                    decision: None,
                });
                None
            } else {
                Some(Effect::RunCommand { family, args })
            }
        }
    }
}

/// Hit-test puro: encuentra la acción que produce un click en (x, y) sobre la
/// pantalla actual. Devuelve `None` si el punto no toca ninguna área.
pub fn hit_test(state: &AppState, x: u16, y: u16) -> Option<AppAction> {
    // B6 — con modal abierto, SOLO sus botones responden (trampa de foco).
    if let Some(p) = state.pending.as_ref() {
        let pos = Position::new(x, y);
        if MODAL_APROBAR_RECT.contains(pos) {
            return Some(AppAction::Approve {
                audit_key: p.req.audit_key.clone(),
            });
        }
        if MODAL_DENEGAR_RECT.contains(pos) {
            return Some(AppAction::Deny {
                audit_key: p.req.audit_key.clone(),
            });
        }
        return None;
    }
    match state.screen {
        Screen::Home => {
            let p = Position::new(x, y);
            if state.areas.home_sessions_btn.is_some_and(|r| r.contains(p)) {
                return Some(AppAction::Navigate(Screen::Sessions));
            }
            if state.areas.home_actions_btn.is_some_and(|r| r.contains(p)) {
                return Some(AppAction::Navigate(Screen::Actions));
            }
            if state
                .areas
                .home_open_session_btn
                .is_some_and(|r| r.contains(p))
            {
                return Some(AppAction::Navigate(Screen::Sessions));
            }
            if state.areas.home_menu_btn.is_some_and(|r| r.contains(p)) {
                return Some(AppAction::Navigate(Screen::Menu));
            }
            None
        }
        Screen::Menu => {
            let p = Position::new(x, y);
            if state.areas.menu_back_btn.is_some_and(|r| r.contains(p)) {
                return Some(AppAction::Back);
            }
            // Filas de la lista: geometría const (misma que render_menu).
            if (MENU_LIST_LEFT..MENU_LIST_LEFT + MENU_LIST_WIDTH).contains(&x)
                && (MENU_LIST_TOP..MENU_LIST_TOP + MENU_LIST_HEIGHT).contains(&y)
            {
                let flat = usize::from(y - MENU_LIST_TOP) + usize::from(state.scroll_offset);
                if let Some(crate::menu::FlatRow::Entry(e)) = crate::menu::row_at(flat) {
                    let args = e.args.iter().map(|s| s.to_string()).collect();
                    return Some(AppAction::RunCommand {
                        family: e.family,
                        args,
                    });
                }
            }
            None
        }
        Screen::Sessions => {
            let pos = Position::new(x, y);
            if SESSIONS_CLOSE_BTN.contains(pos) {
                // Deshabilitado sin selección (misma regla que el render).
                let i = state.sessions.selected?;
                let s = state.sessions.sessions.get(i)?;
                return Some(AppAction::CloseSession {
                    session_id: s.id.clone(),
                });
            }
            if (SESSIONS_LIST_LEFT..SESSIONS_LIST_LEFT + SESSIONS_LIST_WIDTH).contains(&x)
                && (SESSIONS_LIST_TOP..SESSIONS_LIST_TOP + SESSIONS_LIST_HEIGHT).contains(&y)
            {
                let idx = usize::from(y - SESSIONS_LIST_TOP) + usize::from(state.scroll_offset);
                if idx < state.sessions.sessions.len() {
                    return Some(AppAction::SelectSession { index: idx });
                }
            }
            None
        }
        Screen::Actions => {
            let pos = Position::new(x, y);
            if ACTIONS_BATCH_BTN.contains(pos) {
                if batchable_ids(state).is_empty() {
                    return None; // botón deshabilitado
                }
                return Some(AppAction::ApproveBatch);
            }
            if (ACTIONS_APPROVE_X..ACTIONS_APPROVE_X + ACTIONS_APPROVE_W).contains(&x)
                && (ACTIONS_LIST_TOP..ACTIONS_LIST_TOP + ACTIONS_LIST_HEIGHT).contains(&y)
            {
                let idx = usize::from(y - ACTIONS_LIST_TOP) + usize::from(state.scroll_offset);
                if let Some(p) = state.actions.proposals.get(idx) {
                    return Some(AppAction::ApproveProposal { id: p.id.clone() });
                }
            }
            None
        }
        Screen::Search => {
            let p = Position::new(x, y);
            // Fila visible dentro de la ventana de scroll.
            if !(SEARCH_LIST_LEFT..SEARCH_LIST_LEFT + SEARCH_LIST_WIDTH).contains(&x)
                || !(SEARCH_LIST_TOP..SEARCH_LIST_TOP + SEARCH_LIST_HEIGHT).contains(&y)
            {
                return None;
            }
            let idx = usize::from(y - SEARCH_LIST_TOP) + usize::from(state.scroll_offset);
            let h = state.search.hits.get(idx)?.clone();
            // Columna [Útil]: solo filas episódicas con memory_id (semánticos
            // no tienen nada que puntuar — core.py:274).
            if (SEARCH_USEFUL_X..SEARCH_USEFUL_X + SEARCH_USEFUL_W).contains(&x) {
                let id = h.id?;
                return Some(AppAction::MarkUseful { memory_id: id });
            }
            // Cuerpo de la fila: seleccionar (abre el snippet en el detalle).
            let _ = p;
            Some(AppAction::SelectHit { index: idx })
        }
        // B4+ registra áreas por pantalla aquí.
        _ => None,
    }
}

/// Traduce un evento crudo de crossterm a una acción semántica.
/// Mouse = input primario; teclado = accesibilidad (mapeo dual).
pub fn translate_event(ev: &Event) -> Option<AppAction> {
    match ev {
        Event::Mouse(m) => match m.kind {
            MouseEventKind::Down(MouseButton::Left) => Some(AppAction::Click {
                x: m.column,
                y: m.row,
            }),
            MouseEventKind::ScrollDown => Some(AppAction::Scroll { down: true }),
            MouseEventKind::ScrollUp => Some(AppAction::Scroll { down: false }),
            // El hover es mouse-first como el resto: el estado lleva la posición.
            // En crossterm 0.29 `Moved` es unit; las coords están en el MouseEvent.
            MouseEventKind::Moved => Some(AppAction::MouseMoved {
                x: m.column,
                y: m.row,
            }),
            _ => None,
        },
        Event::Key(KeyEvent {
            code, modifiers, ..
        }) => match code {
            KeyCode::Esc => Some(AppAction::Back),
            // Ctrl+C en raw mode NO genera signal (ISIG off): mapeo explícito (B3 review).
            KeyCode::Char('c') if modifiers.contains(KeyModifiers::CONTROL) => {
                Some(AppAction::Quit)
            }
            KeyCode::Char('q') => Some(AppAction::Quit),
            // Carácter tipográfico: entra al input.
            KeyCode::Char(c) => Some(AppAction::Typed(*c)),
            // Teclas no tipográficas: quedan como Key para el foco (B4+).
            other => Some(AppAction::Key(*other)),
        },
        _ => None,
    }
}

/// Versión amigable para el snapshot no-TTY y el render textual mínimo (B3).
pub fn screen_label(s: Screen) -> &'static str {
    match s {
        Screen::Home => "Home",
        Screen::Menu => "Menu",
        Screen::Sessions => "Sessions",
        Screen::Actions => "Actions",
        Screen::Search => "Search",
        Screen::Brain => "Brain",
    }
}
