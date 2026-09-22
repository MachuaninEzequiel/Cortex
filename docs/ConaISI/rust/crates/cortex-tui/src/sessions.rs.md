# rust/crates/cortex-tui/src/sessions.rs

## Qué tiene adentro

Pantalla SESIONES en ratatui (rediseño F2 — spec del agente externo adaptada al repo).  Contrato de DATOS (intacto, Gate CIERRE T6): la pantalla muestra exactamente la misma información que `cortex session list --json` (`_record_summary`): session_id, status, mode, opened_at, closed_at, checkpoint_count y spec_summary — orden newest-first, con marca de sesión activa. La serialización `SessionRow::to_json` no cambió.  Lo NUEVO (diseño, spec §7/§9/§11): tema semántico (`Theme`), glifos de estado (●/○/✓/!/×), tiempos relativos deterministas (reloj inyectado en el snapshot), conteos por status en el header, estados explícitos
Archivo de 436 líneas.
Símbolos públicos observados:
- `pub const RENDER_BUDGET_MS: u128 = 50`
- `pub struct SessionRow`
- `pub struct SessionCounts`
- `pub struct SessionsScreenData`
- `pub fn rel_time(ts: &str, now: DateTime<Utc>, lang: &'static str) -> String`
- `pub struct RenderOpts<'a>`
- `pub fn render(f: &mut Frame<'_>, state: &AppState)`

## Para qué sirve

Pantalla SESIONES en ratatui (rediseño F2 — spec del agente externo adaptada al repo).  Contrato de DATOS (intacto, Gate CIERRE T6): la pantalla muestra exactamente la misma información que `cortex session list --json` (`_record_summary`): session_id, status, mode, opened_at, closed_at, checkpoint_count y spec_summary — orden newest-first, con marca de sesión activa. La serialización `SessionRow::to_json` no cambió.  Lo NUEVO (diseño, spec §7/§9/§11): tema semántico (`Theme`), glifos de estado (●/○/✓/!/×), tiempos relativos deterministas (reloj inyectado en el snapshot), conteos por status en el header, estados explícitos

## Relaciones

### Recibe de

- `use crate::app::state::{AppState, LoadState, Overlay}`
- `use crate::components::empty_state::EmptyState`
- `use crate::components::header::AppHeader`
- `use crate::components::list::SelectableList`
- `use crate::components::status_bar::StatusBar`
- `use crate::components::truncate_visual`
- `use crate::keymap::global_hints`
- `use crate::layout::{layout_mode, render_too_small, LayoutMode}`
- `use crate::theme::{StatusKind, Theme}`
- `use cortex_app::session::service::SessionService`
- `use cortex_app::session::SessionRecord`
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/sessions.rs`.
