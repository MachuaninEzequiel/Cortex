# rust/crates/cortex-tui/src/actions.rs

## Qué tiene adentro

Pantalla ACCIONES (rediseño — reemplaza `render_actions_screen` del oráculo rich, doc 05 §3.5): propuestas del ActionEngine nativo con revisión previa (spec §11.5) y ejecución vía el runner del motor.  Regla del repo: la TUI ORQUESTA el motor, no duplica lógica. El pipeline es EXACTAMENTE el de `cortex next` (ActionContext → registry → PreferencesStore → Scheduler::propose); la ejecución usa `Runner` con su contrato duro (irreversible ⇒ approved explícito, action_log en cada ejecución, dry-run nativo).
Archivo de 531 líneas.
Símbolos públicos observados:
- `pub const RENDER_BUDGET_MS: u128 = 50`
- `pub struct ActionView`
- `pub struct ActionsData`
- `pub fn propose(ctx: &ActionContext, all: bool) -> Result<ActionsData, String>`
- `pub fn context(project_root: Option<&Path>) -> ActionContext`
- `pub fn render(f: &mut Frame<'_>, state: &AppState)`

## Para qué sirve

Pantalla ACCIONES (rediseño — reemplaza `render_actions_screen` del oráculo rich, doc 05 §3.5): propuestas del ActionEngine nativo con revisión previa (spec §11.5) y ejecución vía el runner del motor.  Regla del repo: la TUI ORQUESTA el motor, no duplica lógica. El pipeline es EXACTAMENTE el de `cortex next` (ActionContext → registry → PreferencesStore → Scheduler::propose); la ejecución usa `Runner` con su contrato duro (irreversible ⇒ approved explícito, action_log en cada ejecución, dry-run nativo).

## Relaciones

### Recibe de

- `use crate::app::state::{AppState, LoadState, Overlay}`
- `use crate::components::empty_state::EmptyState`
- `use crate::components::header::AppHeader`
- `use crate::components::help::render_help`
- `use crate::components::panel::draw_panel`
- `use crate::components::status_bar::StatusBar`
- `use crate::components::truncate_visual`
- `use crate::keymap::global_hints`
- `use crate::layout::{layout_mode, render_too_small, LayoutMode}`
- `use crate::theme::{StatusKind, Theme}`
- `use cortex_actions::catalog::build_default_registry`
- `use cortex_actions::context::ActionContext`
- `use cortex_actions::scheduler::Scheduler`
- `use cortex_actions::store::PreferencesStore`
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/actions.rs`.
