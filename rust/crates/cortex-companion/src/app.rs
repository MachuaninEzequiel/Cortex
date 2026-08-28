//! Máquina ELM-lite de la app (G-B2a): estado + acciones semánticas +
//! reducer puro + efectos, e input mouse-first con teclado dual.
//!
//! El render NUNCA muta estado: la UI reduce `AppAction` vía `update` y solo
//! produce un `Effect` opcional que el runtime (binario) aplica. El hit-test
//! es puro: `rects` registradas + coordenadas del click ⇒ `AppAction`.

use crossterm::event::{Event, KeyCode, KeyEvent, KeyModifiers, MouseButton, MouseEventKind};
use ratatui::layout::{Position, Rect};

use crate::menu::MenuOutput;
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
    /// Aprobar/Denegar una mutación propuesta (B2/B6: efectos guarded).
    Approve {
        audit_key: String,
    },
    Deny {
        audit_key: String,
    },
    /// Ejecutar un comando del Menu (B5: lecturas directas o guarded).
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
    /// Ejecutar un comando del catálogo (B5 lo enruta a lectura o guarded).
    RunCommand {
        family: &'static str,
        args: Vec<String>,
    },
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
        }
    }
}

/// Reducer puro: transforma estado + acción ⇒ (posible efecto). No hace I/O.
pub fn update(state: &mut AppState, action: AppAction) -> Option<Effect> {
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
        AppAction::Typed(_) => None,
        // Enter y teclas especiales activan foco en B4+ (data-driven); v1 no-op.
        AppAction::Key(_) => None,
        // Aprobaciones: el efecto guarded llega con B6 (B2 tiene run_guarded).
        AppAction::Approve { .. } | AppAction::Deny { .. } => None,
        AppAction::RunCommand { family, args } => Some(Effect::RunCommand { family, args }),
    }
}

/// Hit-test puro: encuentra la acción que produce un click en (x, y) sobre la
/// pantalla actual. Devuelve `None` si el punto no toca ninguna área.
pub fn hit_test(state: &AppState, x: u16, y: u16) -> Option<AppAction> {
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
