//! Geometría interactiva compartida: LA ÚNICA fuente de verdad de las zonas
//! clickeables. `view.rs` dibuja a partir de estas funciones y el reducer
//! (`update.rs`) hace hit-test con las mismas rectas, de modo que nunca pueden
//! divergir (patrón de `cortex-companion`, adaptado a layouts dinámicos).
//!
//! Todas las funciones son puras: derivan las rects del área (state.size),
//! replicando exactamente los splits de `view::draw`.

use crate::app::state::{AppState, Overlay, Screen, SearchMode};
use crate::app::Action;
use ratatui::layout::{Constraint, Direction, Layout, Margin, Position, Rect};

/// Chunks verticales de la pantalla completa: header(3) | contenido | status(1).
/// Debe coincidir con `view::draw`.
pub fn root_chunks(area: Rect) -> Vec<Rect> {
    Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3), // Header superior
            Constraint::Min(5),    // Pantalla activa
            Constraint::Length(1), // Barra de atajos/status
        ])
        .split(area)
        .to_vec()
}

// ── Barra de status inferior (botones) ─────────────────────────────────────

/// Un botón de la barra de status. `action = None` ⇒ solo informativo.
#[derive(Clone, Debug)]
pub struct StatusHint {
    pub key: &'static str,
    pub label: &'static str,
    pub action: Option<Action>,
}

pub const STATUS_HINTS: &[StatusHint] = &[
    StatusHint { key: "[j/k]", label: "Navegar", action: None },
    StatusHint { key: "[Enter]", label: "Abrir/Copiar", action: Some(Action::Activate) },
    StatusHint { key: "[/]", label: "Buscar", action: Some(Action::OpenSearch) },
    StatusHint { key: "[s]", label: "Sesiones", action: Some(Action::OpenSessions) },
    StatusHint { key: "[a]", label: "Acciones", action: Some(Action::OpenActions) },
    StatusHint { key: "[?]", label: "Ayuda", action: Some(Action::OpenHelp) },
    StatusHint { key: "[q]", label: "Salir", action: Some(Action::QuitRequested) },
];

/// Texto de una celda de status: `" [k] label  "` (celda clickeable completa).
/// Vista y hit-test construyen la geometría desde esta cadena exacta.
pub fn status_cell_text(h: &StatusHint) -> String {
    format!(" {} {}  ", h.key, h.label)
}

/// Rect de cada celda de la barra de status en orden, desde `area.x`.
/// Las celdas que desbordan el área quedan recortadas (la vista las corta
/// igual: un click más allá del borde visible no produce acción).
pub fn status_cells(area: Rect) -> Vec<(Rect, &'static StatusHint)> {
    let mut x = area.x;
    STATUS_HINTS
        .iter()
        .map(|h| {
            let w = status_cell_text(h).chars().count() as u16;
            let avail = area.right().saturating_sub(x);
            let r = Rect::new(x, area.y, w.min(avail), 1);
            x += w;
            (r, h)
        })
        .collect()
}

// ── Home: panel izquierdo con atajos rápidos ──────────────────────────────

/// Prefijo fijo de la línea de atajos del Home (el ancho define el offset x).
pub const HOME_ATAJOS_PREFIX: &str = "Atajos rápidos: ";

/// Botón de atajo dentro del panel izquierdo del Home.
#[derive(Clone, Debug)]
pub struct HomeShortcut {
    pub key: &'static str,
    pub label: &'static str,
    pub action: Action,
}

pub const HOME_SHORTCUTS: &[HomeShortcut] = &[
    HomeShortcut { key: "s", label: "Sesiones", action: Action::OpenSessions },
    HomeShortcut { key: "a", label: "Acciones", action: Action::OpenActions },
    HomeShortcut { key: "/", label: "Buscar", action: Action::OpenSearch },
];

/// Separador entre atajos (definido acá para que vista y hit-test coincidan).
pub const HOME_SHORTCUT_SEP: &str = "  ·  ";

/// Bandas verticales del Home dentro del área de contenido: banner del
/// wordmark (0 si no entra) + paneles. Debe coincidir con `view::draw_home`.
pub struct HomeBands {
    pub banner: Rect,
    pub main: Rect,
}

pub fn home_bands(content: Rect) -> HomeBands {
    let show_banner = content.height >= 21 && content.width >= 56;
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(if show_banner { 8 } else { 0 }),
            Constraint::Min(4),
        ])
        .split(content);
    HomeBands {
        banner: chunks[0],
        main: if show_banner { chunks[1] } else { chunks[0] },
    }
}

/// Columnas exteriores (con borde) de los paneles del Home.
pub fn home_cols_outer(content: Rect) -> (Rect, Rect) {
    let main = home_bands(content).main;
    let cols = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
        .split(main);
    (cols[0], cols[1])
}

/// Inner (sin bordes) de las columnas izquierda/derecha del Home.
pub fn home_cols(content: Rect) -> (Rect, Rect) {
    let (l, r) = home_cols_outer(content);
    (l.inner(Margin::new(1, 1)), r.inner(Margin::new(1, 1)))
}

/// Fila (dentro del inner del panel izquierdo) donde vive la línea de atajos:
/// 0 salud · 1 vacío · 2 vault · 3 acciones · 4 vacío · 5 atajos.
pub const HOME_ATAJOS_ROW: u16 = 5;

/// Texto de un atajo: `[s] Sesiones`.
pub fn home_shortcut_text(s: &HomeShortcut) -> String {
    format!("[{}] {}", s.key, s.label)
}

/// Rect de cada atajo clickeable del Home.
pub fn home_shortcut_cells(content: Rect) -> Vec<(Rect, &'static HomeShortcut)> {
    let (left, _) = home_cols(content);
    let mut x = left.x + HOME_ATAJOS_PREFIX.chars().count() as u16;
    let y = left.y + HOME_ATAJOS_ROW;
    HOME_SHORTCUTS
        .iter()
        .enumerate()
        .map(|(i, s)| {
            if i > 0 {
                x += HOME_SHORTCUT_SEP.chars().count() as u16;
            }
            let w = home_shortcut_text(s).chars().count() as u16;
            let r = Rect::new(x, y, w, 1);
            x += w;
            (r, s)
        })
        .collect()
}

// ── Listas de sesiones / acciones / resultados de búsqueda ────────────────

/// Filas de 2 celdas por ítem (Búsqueda dibuja título + path).
pub const SEARCH_ROW_H: u16 = 2;

/// División de la pantalla de búsqueda: input arriba (3), resultados abajo.
fn search_split(content: Rect) -> (Rect, Rect) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Length(3), Constraint::Min(4)])
        .split(content);
    (chunks[0], chunks[1])
}

/// Índice de fila a partir de la y del click, dado el alto por fila.
fn row_index(inner: Rect, y: u16, row_h: u16) -> Option<usize> {
    let dy = y.checked_sub(inner.y)?;
    Some((dy / row_h.max(1)) as usize)
}

// ── hover y hit-test ───────────────────────────────────────────────────────

pub fn hovered(state: &AppState, cell: Rect) -> bool {
    state
        .hover
        .is_some_and(|(x, y)| cell.contains(Position::new(x, y)))
}

/// Traduce un click (x, y) en una acción semántica. `None` = click sin destino.
pub fn hit_test(state: &AppState, x: u16, y: u16) -> Option<Action> {
    // Overlay abierto: cualquier click lo cierra (Back ya cancela modales).
    if state.overlay != Overlay::None {
        return Some(Action::Back);
    }
    let area = Rect::new(0, 0, state.size.0, state.size.1);
    let chunks = root_chunks(area);
    let (content, status) = (chunks[1], chunks[2]);

    // Barra de status inferior: botones.
    if y == status.y {
        return status_cells(status).into_iter().find_map(|(cell, h)| {
            cell.contains(Position::new(x, y)).then(|| h.action.clone()).flatten()
        });
    }
    // Header y fuera del contenido: sin zonas clickeables.
    if y < content.y || y >= content.y + content.height {
        return None;
    }
    match state.screen {
        Screen::Home => home_shortcut_cells(content)
            .into_iter()
            .find_map(|(cell, s)| cell.contains(Position::new(x, y)).then(|| s.action.clone())),
        Screen::Sessions | Screen::Actions => {
            let inner = content.inner(Margin::new(1, 1));
            if !inner.contains(Position::new(x, y)) {
                return None;
            }
            row_index(inner, y, 1)
                .and_then(|i| (i < state.list_len()).then_some(Action::RowClick { index: i }))
        }
        Screen::Search => {
            let (input, results) = search_split(content);
            if input.contains(Position::new(x, y)) {
                // Click en el input: vuelve al modo edición desde resultados.
                return (state.search_mode == SearchMode::List).then_some(Action::OpenSearch);
            }
            let inner = results.inner(Margin::new(1, 1));
            if !inner.contains(Position::new(x, y)) {
                return None;
            }
            row_index(inner, y, SEARCH_ROW_H)
                .and_then(|i| (i < state.list_len()).then_some(Action::RowClick { index: i }))
        }
        Screen::SessionDetail => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::app::state::AppState;

    fn state_at(screen: Screen) -> AppState {
        let mut s = AppState::with_screen(screen, "es", (100, 30));
        s.sessions = crate::app::state::LoadState::Ready(Default::default());
        s
    }

    #[test]
    fn click_en_boton_status_produce_su_accion() {
        let s = state_at(Screen::Home);
        let area = Rect::new(0, 0, 100, 30);
        let status = root_chunks(area)[2];
        let (cell, _hint) = status_cells(status)
            .into_iter()
            .find(|(_, h)| h.key == "[/]")
            .expect("falta botón Buscar");
        let action = hit_test(&s, cell.x + 1, status.y).unwrap();
        assert!(matches!(action, Action::OpenSearch));
    }

    #[test]
    fn click_status_informativo_no_hace_nada() {
        let s = state_at(Screen::Home);
        let area = Rect::new(0, 0, 100, 30);
        let status = root_chunks(area)[2];
        let (cell, _) = status_cells(status)
            .into_iter()
            .find(|(_, h)| h.key == "[j/k]")
            .unwrap();
        assert!(hit_test(&s, cell.x + 1, status.y).is_none());
    }

    #[test]
    fn overlay_cualquier_click_es_back() {
        let mut s = state_at(Screen::Home);
        s.overlay = Overlay::Help;
        assert!(matches!(hit_test(&s, 50, 15), Some(Action::Back)));
    }

    #[test]
    fn atajos_del_home_caen_sobre_la_linea_correcta() {
        let s = state_at(Screen::Home);
        let content = root_chunks(Rect::new(0, 0, 100, 30))[1];
        for (cell, shortcut) in home_shortcut_cells(content) {
            assert!(cell.x >= content.x + 1 && cell.y < content.y + content.height);
            let action = hit_test(&s, cell.x + 1, cell.y).unwrap();
            assert_eq!(action, shortcut.action.clone());
        }
    }

    #[test]
    fn click_sobre_el_input_de_busqueda_reabre_el_modo_edicion() {
        let mut s = state_at(Screen::Search);
        s.search_mode = SearchMode::List;
        let content = root_chunks(Rect::new(0, 0, 100, 30))[1];
        let (input, _) = search_split(content);
        let a = hit_test(&s, input.x + 2, input.y + 1).unwrap();
        assert!(matches!(a, Action::OpenSearch));
    }
}
