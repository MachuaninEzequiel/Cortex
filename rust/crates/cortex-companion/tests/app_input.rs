//! Tests de la máquina de estado (G-B2a): AppAction / AppState / update /
//! hit_test / translate_event — mouse-first + teclado dual, sin terminal real.

use std::path::PathBuf;

use crossterm::event::{
    Event, KeyCode, KeyEvent, KeyModifiers, MouseButton, MouseEvent, MouseEventKind,
};
use ratatui::layout::Position;

use cortex_companion::app::{
    hit_test, translate_event, update, AppAction, AppState, Effect, HOME_SESSIONS_BTN,
};
use cortex_companion::{Screen, UiRequest};

fn req() -> UiRequest {
    UiRequest {
        screen: Screen::Home,
        project_root: PathBuf::from("/tmp/fixture"),
    }
}

#[test]
fn mouse_click_on_nav_screen_navigates() {
    let mut st = AppState::new(req());
    assert_eq!(st.screen, Screen::Home);
    let btn = HOME_SESSIONS_BTN;
    let cx = btn.x + btn.width / 2;
    let cy = btn.y;
    let action = hit_test(&st, cx, cy).expect("debe haber un botón en (cx, cy)");
    assert!(matches!(action, AppAction::Navigate(Screen::Sessions)));
    assert!(update(&mut st, action).is_none());
    assert_eq!(st.screen, Screen::Sessions);
    // back vuelve al Home
    assert!(update(&mut st, AppAction::Back).is_none());
    assert_eq!(st.screen, Screen::Home);
}

#[test]
fn click_outside_any_area_is_none() {
    let st = AppState::new(req());
    assert!(hit_test(&st, 0, 0).is_none()); // lejos de cualquier botón
}

#[test]
fn scroll_down_translates_to_scroll_down() {
    let ev = Event::Mouse(MouseEvent {
        kind: MouseEventKind::ScrollDown,
        column: 0,
        row: 0,
        modifiers: KeyModifiers::NONE,
    });
    assert_eq!(translate_event(&ev), Some(AppAction::Scroll { down: true }));
}

#[test]
fn scroll_up_translates_to_scroll_up() {
    let ev = Event::Mouse(MouseEvent {
        kind: MouseEventKind::ScrollUp,
        column: 0,
        row: 0,
        modifiers: KeyModifiers::NONE,
    });
    assert_eq!(
        translate_event(&ev),
        Some(AppAction::Scroll { down: false })
    );
}

#[test]
fn mouse_left_click_translates_to_click_with_coords() {
    let ev = Event::Mouse(MouseEvent {
        kind: MouseEventKind::Down(MouseButton::Left),
        column: 13,
        row: 7,
        modifiers: KeyModifiers::NONE,
    });
    assert_eq!(translate_event(&ev), Some(AppAction::Click { x: 13, y: 7 }));
}

#[test]
fn keyboard_esc_equivalent_to_back() {
    let ev = Event::Key(KeyEvent::new(KeyCode::Esc, KeyModifiers::NONE));
    assert_eq!(translate_event(&ev), Some(AppAction::Back));
}

#[test]
fn keyboard_q_equivalent_to_quit() {
    // Fix B7 (finding review): 'q' ya NO es Quit a nivel traducción — pasa por
    // Typed y el reducer decide según pantalla (en Search es texto de consulta).
    let ev = Event::Key(KeyEvent::new(KeyCode::Char('q'), KeyModifiers::NONE));
    assert_eq!(translate_event(&ev), Some(AppAction::Typed('q')));
}

#[test]
fn q_in_search_types_into_query_and_never_quits() {
    // Regresión Critical (review B7): tipear una consulta con 'q' ("query",
    // "equipo", "qa") mataba el proceso a mitad de edición. Ahora 'q' entra a
    // la query y NO setea quit. Full-path: translate_event + update.
    let ev = Event::Key(KeyEvent::new(KeyCode::Char('q'), KeyModifiers::NONE));
    let act = translate_event(&ev).expect("'q' debe traducirse a acción");
    let mut st = AppState::new(UiRequest {
        screen: Screen::Search,
        project_root: PathBuf::from("/tmp/fixture"),
    });
    st.search.query.push_str("uery-before");
    assert!(update(&mut st, act).is_none());
    assert!(!st.quit, "'q' dentro de Search NO debe setear quit");
    assert!(
        st.search.query.starts_with("uery-beforeq"),
        "la query debe recibir el carácter 'q': {:?}",
        st.search.query
    );
}

#[test]
fn q_outside_search_still_quits() {
    // El contrato global se conserva: fuera de Search, 'q' sigue cerrando.
    let ev = Event::Key(KeyEvent::new(KeyCode::Char('q'), KeyModifiers::NONE));
    let act = translate_event(&ev).expect("'q' debe traducirse a acción");
    let mut st = AppState::new(req()); // Home
    update(&mut st, act);
    assert!(st.quit, "'q' fuera de Search debe seguir cerrando");
}

#[test]
fn ctrl_c_quits_even_from_search() {
    // El fix no desactiva la salida de emergencia: Ctrl+C (mapeo explícito a
    // Quit, B3) cierra también desde Search, donde 'q' es texto.
    let ev = Event::Key(KeyEvent::new(KeyCode::Char('c'), KeyModifiers::CONTROL));
    let act = translate_event(&ev).expect("Ctrl+C debe traducirse a Quit");
    let mut st = AppState::new(UiRequest {
        screen: Screen::Search,
        project_root: PathBuf::from("/tmp/fixture"),
    });
    update(&mut st, act);
    assert!(st.quit, "Ctrl+C debe cerrar incluso desde Search");
}

#[test]
fn typed_char_passes_through() {
    let ev = Event::Key(KeyEvent::new(KeyCode::Char('a'), KeyModifiers::NONE));
    assert_eq!(translate_event(&ev), Some(AppAction::Typed('a')));
}

#[test]
fn enter_maps_to_key_for_future_focus_activation() {
    let ev = Event::Key(KeyEvent::new(KeyCode::Enter, KeyModifiers::NONE));
    assert_eq!(translate_event(&ev), Some(AppAction::Key(KeyCode::Enter)));
}

#[test]
fn quit_sets_quit_flag() {
    let mut st = AppState::new(req());
    assert!(!st.quit);
    assert!(update(&mut st, AppAction::Quit).is_none());
    assert!(st.quit);
}

#[test]
fn run_command_declares_effect() {
    let mut st = AppState::new(req());
    let fx = update(
        &mut st,
        AppAction::RunCommand {
            family: "doctor",
            args: vec![],
        },
    );
    assert_eq!(
        fx,
        Some(Effect::RunCommand {
            family: "doctor",
            args: vec![],
        })
    );
}

#[test]
fn scroll_on_empty_state_is_noop() {
    let mut st = AppState::new(req());
    assert!(update(&mut st, AppAction::Scroll { down: true }).is_none());
    assert_eq!(st.screen, Screen::Home);
}

// hit-test usa Position de ratatui 0.30 (contiene x+width).
#[test]
fn home_button_contains_its_center() {
    let r = HOME_SESSIONS_BTN;
    assert!(r.contains(Position::new(r.x + r.width / 2, r.y)));
}

// Back sobre pila vacía es no-op (sin panic, pantalla intacta).
#[test]
fn back_on_empty_stack_is_noop() {
    let mut st = AppState::new(req());
    assert!(update(&mut st, AppAction::Back).is_none());
    assert_eq!(st.screen, Screen::Home);
}
