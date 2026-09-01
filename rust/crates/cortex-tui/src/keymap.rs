//! Mapa de teclas → acciones semánticas (spec §12): un solo lugar decide
//! qué gesto hace qué, según contexto (overlay abierto, input activo).
//! La ayuda se genera desde acá — nunca se duplica como texto hardcodeado.

use crate::app::{Action, Overlay, Screen};
use ratatui::crossterm::event::{KeyCode, KeyEvent, KeyEventKind, KeyModifiers};

/// Contexto de teclado: qué capa tiene el foco y en qué pantalla.
#[derive(Clone, Copy, Debug)]
pub struct KeyContext {
    /// Input de texto activo (las letras escriben, no navegan).
    pub in_input: bool,
    /// Overlay abierto (focus trap: las teclas no afectan la pantalla).
    pub overlay: Overlay,
    /// Pantalla activa (teclas de acceso directo por pantalla).
    pub screen: Screen,
}

impl KeyContext {
    pub fn normal() -> Self {
        Self {
            in_input: false,
            overlay: Overlay::None,
            screen: Screen::Home,
        }
    }
}

/// Traduce un evento de tecla a acción. `None` = gesto sin efecto (no
/// llenar la UI de errores por gestos no aplicables — spec §12).
pub fn key_to_action(key: KeyEvent, ctx: KeyContext) -> Option<Action> {
    if key.kind != KeyEventKind::Press && key.kind != KeyEventKind::Repeat {
        return None; // Release ignorado (spec §12)
    }
    let ctrl = key.modifiers.contains(KeyModifiers::CONTROL);

    if ctx.overlay != Overlay::None {
        // Focus trap: solo se manejan Esc/?/q queda bloqueado. El modal de
        // confirmación acepta Enter (revisión previa, spec §11.5).
        return match (key.code, ctx.overlay) {
            (KeyCode::Esc, _) => Some(Action::Back),
            (KeyCode::Char('?'), Overlay::Help) => Some(Action::CloseOverlay),
            (KeyCode::Enter, Overlay::Confirm { .. }) => Some(Action::ConfirmArm),
            _ => None,
        };
    }

    if ctx.in_input {
        return match (key.code, ctrl) {
            (KeyCode::Esc, _) => Some(Action::Back),
            (KeyCode::Enter, _) => Some(Action::Submit),
            (KeyCode::Backspace, _) => Some(Action::Backspace),
            (KeyCode::Char(c), false) if !c.is_control() => Some(Action::Input(c)),
            _ => None,
        };
    }

    match (key.code, ctrl) {
        (KeyCode::Up, _) | (KeyCode::Char('k'), false) => Some(Action::MoveUp),
        (KeyCode::Down, _) | (KeyCode::Char('j'), false) => Some(Action::MoveDown),
        (KeyCode::Home, _) | (KeyCode::Char('g'), false) => Some(Action::GoTop),
        (KeyCode::End, _) | (KeyCode::Char('G'), false) => Some(Action::GoBottom),
        (KeyCode::PageUp, _) | (KeyCode::Char('u'), true) => Some(Action::PageUp),
        (KeyCode::PageDown, _) | (KeyCode::Char('d'), true) => Some(Action::PageDown),
        (KeyCode::Tab, false) => Some(Action::FocusNext),
        (KeyCode::BackTab, _) => Some(Action::FocusPrevious),
        (KeyCode::Enter, _) => Some(Action::Activate),
        (KeyCode::Esc, _) | (KeyCode::Char('b'), false) => Some(Action::Back),
        (KeyCode::Char('/'), _) => Some(Action::OpenSearch),
        (KeyCode::Char('?'), _) => Some(Action::OpenHelp),
        (KeyCode::Char('q'), false) => Some(Action::QuitRequested),
        (KeyCode::Char('c'), true) => Some(Action::QuitRequested),
        (KeyCode::Char('n'), false) => Some(Action::DismissNotification),
        // Accesos directos históricos de Cortex: a=acciones, s=sesión
        // (navegan solo cuando aplican en la pantalla actual).
        (KeyCode::Char('a'), false) if ctx.screen != Screen::Actions => Some(Action::OpenActions),
        (KeyCode::Char('s'), false) if ctx.screen != Screen::Sessions => Some(Action::OpenSessions),
        // Dentro de Acciones, `a` es el lote auto-ok (doc 05 §3.5).
        (KeyCode::Char('a'), false) if ctx.screen == Screen::Actions => Some(Action::ApproveAutoOk),
        // `y` marca útil el hit de búsqueda seleccionado (feedback).
        (KeyCode::Char('y'), false) if ctx.screen == Screen::Search => Some(Action::MarkUseful),
        // `c` copia la selección (id de sesión o ruta del hit).
        (KeyCode::Char('c'), false) => Some(Action::CopySelection),
        _ => None,
    }
}

/// Pares (tecla, descripción) del mapa GLOBAL — fuente de la ayuda y del
/// command bar (spec §10: mostrar 3-5 acciones prioritarias; `?` muestra
/// el mapa completo).
pub fn global_hints(lang: &'static str) -> Vec<(&'static str, &'static str)> {
    let nav = if lang == "en" { "navigate" } else { "navegar" };
    let quit = if lang == "en" { "quit" } else { "salir" };
    let help = if lang == "en" { "help" } else { "ayuda" };
    vec![("j/k", nav), ("/", "search"), ("?", help), ("q", quit)]
}

/// Mapa completo para la pantalla de ayuda (F4 consume; F2 ya expone).
pub fn full_help(lang: &'static str) -> Vec<(&'static str, &'static str)> {
    let mut rows = global_hints(lang);
    rows.extend([
        (
            "g/G",
            if lang == "en" {
                "top/bottom"
            } else {
                "inicio/fin"
            },
        ),
        (
            "Ctrl+U/D",
            if lang == "en" {
                "page up/down"
            } else {
                "página arriba/abajo"
            },
        ),
        (
            "Tab",
            if lang == "en" {
                "next panel"
            } else {
                "siguiente panel"
            },
        ),
        ("Esc", if lang == "en" { "back" } else { "volver" }),
        ("Enter", if lang == "en" { "open" } else { "abrir" }),
    ]);
    rows
}

#[cfg(test)]
mod tests {
    use super::*;

    fn key(code: KeyCode, ctrl: bool) -> KeyEvent {
        KeyEvent {
            code,
            modifiers: if ctrl {
                KeyModifiers::CONTROL
            } else {
                KeyModifiers::NONE
            },
            kind: KeyEventKind::Press,
            state: ratatui::crossterm::event::KeyEventState::empty(),
        }
    }

    #[test]
    fn j_k_y_flechas_producen_lo_mismo() {
        assert_eq!(
            key_to_action(key(KeyCode::Char('j'), false), KeyContext::normal()),
            key_to_action(key(KeyCode::Down, false), KeyContext::normal())
        );
        assert_eq!(
            key_to_action(key(KeyCode::Char('k'), false), KeyContext::normal()),
            key_to_action(key(KeyCode::Up, false), KeyContext::normal())
        );
    }

    #[test]
    fn release_es_ignorado() {
        let mut k = key(KeyCode::Char('j'), false);
        k.kind = KeyEventKind::Release;
        assert_eq!(key_to_action(k, KeyContext::normal()), None);
    }

    #[test]
    fn q_no_sale_con_overlay() {
        assert_eq!(
            key_to_action(
                key(KeyCode::Char('q'), false),
                KeyContext {
                    in_input: false,
                    overlay: Overlay::Help,
                    screen: Screen::Home,
                },
            ),
            None
        );
        // Esc sí cierra el overlay.
        assert_eq!(
            key_to_action(
                key(KeyCode::Esc, false),
                KeyContext {
                    in_input: false,
                    overlay: Overlay::Help,
                    screen: Screen::Home,
                }
            ),
            Some(Action::Back)
        );
    }

    #[test]
    fn enter_arma_confirmacion_dentro_del_modal() {
        let ctx = KeyContext {
            in_input: false,
            overlay: Overlay::Confirm {
                index: 0,
                armed: false,
            },
            screen: Screen::Actions,
        };
        assert_eq!(
            key_to_action(key(KeyCode::Enter, false), ctx),
            Some(Action::ConfirmArm)
        );
        // q sigue bloqueado en el modal de confirmación.
        assert_eq!(key_to_action(key(KeyCode::Char('q'), false), ctx), None);
        // Esc cancela (Back cierra el overlay en el reducer).
        assert_eq!(
            key_to_action(key(KeyCode::Esc, false), ctx),
            Some(Action::Back)
        );
    }

    #[test]
    fn en_input_las_letras_escriben() {
        let ctx = KeyContext {
            in_input: true,
            overlay: Overlay::None,
            screen: Screen::Home,
        };
        assert_eq!(
            key_to_action(key(KeyCode::Char('a'), false), ctx),
            Some(Action::Input('a'))
        );
        assert_eq!(
            key_to_action(key(KeyCode::Backspace, false), ctx),
            Some(Action::Backspace)
        );
        assert_eq!(
            key_to_action(key(KeyCode::Enter, false), ctx),
            Some(Action::Submit)
        );
        // j/k no navegan dentro del input.
        assert_eq!(
            key_to_action(key(KeyCode::Char('j'), false), ctx),
            Some(Action::Input('j'))
        );
        // q no sale dentro del input.
        assert_eq!(
            key_to_action(key(KeyCode::Char('q'), false), ctx),
            Some(Action::Input('q'))
        );
    }

    #[test]
    fn ayuda_se_deriva_del_mapa() {
        let help = full_help("es");
        assert!(help.iter().any(|(k, _)| *k == "j/k"));
        assert!(help.iter().any(|(k, _)| *k == "?"));
    }

    #[test]
    fn accesos_directos_por_pantalla() {
        let home = KeyContext::normal(); // screen Home
        assert_eq!(
            key_to_action(key(KeyCode::Char('a'), false), home),
            Some(Action::OpenActions)
        );
        assert_eq!(
            key_to_action(key(KeyCode::Char('s'), false), home),
            Some(Action::OpenSessions)
        );
        // En la pantalla Acciones, 'a' es el lote auto-ok.
        let actions = KeyContext {
            in_input: false,
            overlay: Overlay::None,
            screen: Screen::Actions,
        };
        assert_eq!(
            key_to_action(key(KeyCode::Char('a'), false), actions),
            Some(Action::ApproveAutoOk)
        );
        // 'y' marca útil solo en búsqueda; 'c' copia la selección.
        let search = KeyContext {
            in_input: false,
            overlay: Overlay::None,
            screen: Screen::Search,
        };
        assert_eq!(
            key_to_action(key(KeyCode::Char('y'), false), search),
            Some(Action::MarkUseful)
        );
        assert_eq!(key_to_action(key(KeyCode::Char('y'), false), actions), None);
        assert_eq!(
            key_to_action(key(KeyCode::Char('c'), false), search),
            Some(Action::CopySelection)
        );
        // 'b' es volver (además de Esc).
        assert_eq!(
            key_to_action(key(KeyCode::Char('b'), false), home),
            Some(Action::Back)
        );
    }
}
