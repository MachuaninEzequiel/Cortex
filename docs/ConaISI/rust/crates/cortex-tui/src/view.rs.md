# rust/crates/cortex-tui/src/view.rs

## Qué tiene adentro

Renderizado modular y funciones de vista (spec §2 / §4 / §5).  Todas las vistas son funciones puras que reciben `&AppState` y `&Theme`, garantizando testeabilidad con `TestBackend` sin efectos colaterales.
Archivo de 542 líneas.
Símbolos públicos observados:
- `pub fn draw(frame: &mut Frame<'_>, state: &AppState, theme: &Theme)`
- `pub fn draw_header(frame: &mut Frame<'_>, area: Rect, state: &AppState, theme: &Theme)`
- `pub fn draw_home(frame: &mut Frame<'_>, area: Rect, state: &AppState, theme: &Theme)`
- `pub fn draw_sddwork(frame: &mut Frame<'_>, area: Rect, _state: &AppState, theme: &Theme)`
- `pub fn draw_sessions(frame: &mut Frame<'_>, area: Rect, state: &AppState, theme: &Theme)`
- `pub fn draw_session_detail(frame: &mut Frame<'_>, area: Rect, state: &AppState, theme: &Theme)`
- `pub fn draw_actions(frame: &mut Frame<'_>, area: Rect, state: &AppState, theme: &Theme)`
- `pub fn draw_search(frame: &mut Frame<'_>, area: Rect, state: &AppState, theme: &Theme)`
- `pub fn draw_status_bar(frame: &mut Frame<'_>, area: Rect, state: &AppState, theme: &Theme)`
- `pub fn draw_overlay(frame: &mut Frame<'_>, area: Rect, state: &AppState, theme: &Theme)`
- `pub fn draw_3d_wordmark(buf: &mut ratatui::buffer::Buffer, area: Rect, theme: &Theme)`

## Para qué sirve

Renderizado modular y funciones de vista (spec §2 / §4 / §5).  Todas las vistas son funciones puras que reciben `&AppState` y `&Theme`, garantizando testeabilidad con `TestBackend` sin efectos colaterales.

## Relaciones

### Recibe de

- `use crate::app::{AppState, LoadState, Overlay, Screen}`
- `use crate::theme::Theme`
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/view.rs`.
