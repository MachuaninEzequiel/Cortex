//! Eventos y mapeo de teclas/mouse a acciones semánticas (spec §2).

pub use crate::app::Action;
pub use crate::keymap::{key_to_action, KeyContext};
use ratatui::crossterm::event::{Event, MouseButton, MouseEvent, MouseEventKind};

/// Traduce un evento de mouse en una acción semántica (input primario;
/// el teclado permanece como accesibilidad, igual que en companion).
pub fn mouse_to_action(m: MouseEvent) -> Option<Action> {
    match m.kind {
        MouseEventKind::Down(MouseButton::Left) => Some(Action::Click { x: m.column, y: m.row }),
        MouseEventKind::ScrollUp => Some(Action::Scroll { down: false }),
        MouseEventKind::ScrollDown => Some(Action::Scroll { down: true }),
        // crossterm 0.29: `Moved` trae las coords en el MouseEvent.
        MouseEventKind::Moved => Some(Action::Hover { x: m.column, y: m.row }),
        _ => None,
    }
}

/// Traduce un evento de crossterm a una acción semántica de la TUI.
pub fn map_event(event: Event, ctx: KeyContext) -> Option<Action> {
    match event {
        Event::Key(key) => key_to_action(key, ctx),
        Event::Mouse(m) => mouse_to_action(m),
        Event::Resize(w, h) => Some(Action::Resize { width: w, height: h }),
        _ => None,
    }
}
