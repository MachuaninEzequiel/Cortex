# rust/crates/cortex-tui/src/home.rs

## Qué tiene adentro

Home de Cortex en ratatui — espejo de `cortex/tui/core.py` (Obra 05 Fase D).  `HomeState` replica campo a campo el snapshot barato del Home Python; el cableado a servicios reales (sessions/acciones/vault vía cortex-app) llega con F4 del rediseño. Mientras tanto `demo_state()` provee datos de muestra para el gate P10: snapshot render + latencia <50ms.  Rediseño F2: todo el estilo pasa por `Theme` (sin `Color::Rgb` sueltos); el ámbar ad-hoc de avisos se reemplazó por el token semántico WARNING.
Archivo de 363 líneas.
Símbolos públicos observados:
- `pub const RENDER_BUDGET_MS: u128 = 50`
- `pub struct HomeState`
- `pub fn demo_state() -> HomeState`
- `pub fn snapshot(ctx: &ActionContext, service: Option<&SessionService>) -> HomeState`
- `pub fn branch_from_head(repo_root: &Path) -> Option<String>`
- `pub fn count_markdown(dir: &Path) -> usize`
- `pub fn render(f: &mut Frame<'_>, state: &HomeState)`

## Para qué sirve

Home de Cortex en ratatui — espejo de `cortex/tui/core.py` (Obra 05 Fase D).  `HomeState` replica campo a campo el snapshot barato del Home Python; el cableado a servicios reales (sessions/acciones/vault vía cortex-app) llega con F4 del rediseño. Mientras tanto `demo_state()` provee datos de muestra para el gate P10: snapshot render + latencia <50ms.  Rediseño F2: todo el estilo pasa por `Theme` (sin `Color::Rgb` sueltos); el ámbar ad-hoc de avisos se reemplazó por el token semántico WARNING.

## Relaciones

### Recibe de

- `use crate::app::state::Notification`
- `use crate::components::status_bar::StatusBar`
- `use crate::layout::{layout_mode, LayoutMode}`
- `use crate::renderer::CortexLogo`
- `use crate::theme::{brand_text, StatusKind, Theme}`
- `use crate::{env_color_mode, lang, LogoVariant}`
- `use cortex_actions::catalog::build_default_registry`
- `use cortex_actions::context::ActionContext`
- `use cortex_actions::scheduler::Scheduler`
- `use cortex_actions::store::PreferencesStore`
- `use cortex_app::session::service::SessionService`
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/home.rs`.
