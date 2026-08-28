//! Máquina ELM-lite de la app (G-B2a): estado + acciones semánticas +
//! reducer puro + efectos, e input mouse-first con teclado dual.
//!
//! El render NUNCA muta estado: la UI reduce `AppAction` vía `update` y solo
//! produce un `Effect` opcional que el runtime (binario) aplica. El hit-test
//! es puro: `rects` registradas + coordenadas del click ⇒ `AppAction`.

use crossterm::event::{Event, KeyCode, KeyEvent, MouseButton, MouseEventKind};
use ratatui::layout::{Position, Rect};

use crate::{Screen, UiRequest};

/// Rect canónica del botón "Sesiones" en el Home. Los tests de B3 la usan y
/// B4 (layout real del Home) la ajusta SI hace falta — actualizando ambos.
pub const HOME_SESSIONS_BTN: Rect = Rect::new(2, 4, 18, 1);

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
    /// Offset de scroll actual (v1: preservado, consumido por pantallas en B4+).
    pub scroll_offset: u16,
}

impl AppState {
    pub fn new(req: UiRequest) -> Self {
        Self {
            screen: req.screen,
            stack: Vec::new(),
            areas: Areas {
                home_sessions_btn: Some(HOME_SESSIONS_BTN),
            },
            quit: false,
            scroll_offset: 0,
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
        // v1 no hay scroll por pantalla aún; preservar offset cuando B4+ lo use.
        AppAction::Scroll { down } => {
            state.scroll_offset = state.scroll_offset.saturating_add(if down { 1 } else { 0 });
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
        Screen::Home => state
            .areas
            .home_sessions_btn
            .filter(|r| r.contains(Position::new(x, y)))
            .map(|_| AppAction::Navigate(Screen::Sessions)),
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
            _ => None,
        },
        Event::Key(KeyEvent { code, .. }) => match code {
            KeyCode::Esc => Some(AppAction::Back),
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
