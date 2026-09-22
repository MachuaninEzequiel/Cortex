# rust/crates/cortex-tui/src/hit.rs

## Qué tiene adentro

Geometría interactiva compartida: LA ÚNICA fuente de verdad de las zonas clickeables. `view.rs` dibuja a partir de estas funciones y el reducer (`update.rs`) hace hit-test con las mismas rectas, de modo que nunca pueden divergir (patrón de `cortex-companion`, adaptado a layouts dinámicos).  Todas las funciones son puras: derivan las rects del área (state.size), replicando exactamente los splits de `view::draw`.
Archivo de 299 líneas.
Símbolos públicos observados:
- `pub fn root_chunks(area: Rect) -> Vec<Rect>`
- `pub struct StatusHint`
- `pub const STATUS_HINTS: &[StatusHint] = &[`
- `pub fn status_cell_text(h: &StatusHint) -> String`
- `pub fn status_cells(area: Rect) -> Vec<(Rect, &'static StatusHint)>`
- `pub const HOME_ATAJOS_PREFIX: &str = "Atajos rápidos: "`
- `pub struct HomeShortcut`
- `pub const HOME_SHORTCUTS: &[HomeShortcut] = &[`
- `pub const HOME_SHORTCUT_SEP: &str = "  ·  "`
- `pub struct HomeBands`
- `pub fn home_bands(content: Rect) -> HomeBands`
- `pub fn home_cols_outer(content: Rect) -> (Rect, Rect)`
- `pub fn home_cols(content: Rect) -> (Rect, Rect)`
- `pub const HOME_ATAJOS_ROW: u16 = 5`
- `pub fn home_shortcut_text(s: &HomeShortcut) -> String`
- `pub fn home_shortcut_cells(content: Rect) -> Vec<(Rect, &'static HomeShortcut)>`
- `pub const SEARCH_ROW_H: u16 = 2`
- `pub fn hovered(state: &AppState, cell: Rect) -> bool`
- `pub fn hit_test(state: &AppState, x: u16, y: u16) -> Option<Action>`
Tests en el mismo archivo: `click_en_boton_status_produce_su_accion`, `click_status_informativo_no_hace_nada`, `overlay_cualquier_click_es_back`, `atajos_del_home_caen_sobre_la_linea_correcta`, `click_sobre_el_input_de_busqueda_reabre_el_modo_edicion`

## Para qué sirve

Geometría interactiva compartida: LA ÚNICA fuente de verdad de las zonas clickeables. `view.rs` dibuja a partir de estas funciones y el reducer (`update.rs`) hace hit-test con las mismas rectas, de modo que nunca pueden divergir (patrón de `cortex-companion`, adaptado a layouts dinámicos).  Todas las funciones son puras: derivan las rects del área (state.size), replicando exactamente los splits de `view::draw`.

## Relaciones

### Recibe de

- `use crate::app::state::{AppState, Overlay, Screen, SearchMode}`
- `use crate::app::Action`
- `use crate::app::state::AppState`
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/hit.rs`.
