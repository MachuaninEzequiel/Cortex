# rust/crates/cortex-tui/src/app/runtime.rs

## Qué tiene adentro

Runtime unificado de la TUI (spec §2/§6): un solo loop para todas las pantallas, con historial de navegación, efectos ejecutados FUERA del reducer y restauración RAII. Los loops individuales de F2 (sessions::run / actions::run) se consolidan acá; las pantallas solo renderizan.  Reglas: - el runtime recarga el snapshot de la pantalla ACTUAL en cada tick (mismo comportamiento que el oráculo: tiempos relativos frescos); - las acciones del motor se ejecutan en un thread (feedback en vivo, spinner por tick; F3 async pleno puede reemplazar el thread); - el detalle de sesión se carga por efecto (`LoadSessionDetail`).
Archivo de 406 líneas.
Símbolos públicos observados:
- `pub const TICK_MS: u64 = 250`
- `pub const SPINNER: [&str`
- `pub struct UiRequest<'a>`
- `pub fn snapshot(req: UiRequest<'_>, w: u16, h: u16) -> Result<String, String>`
- `pub fn run(req: UiRequest<'_>) -> Result<(), String>`

## Para qué sirve

Runtime unificado de la TUI (spec §2/§6): un solo loop para todas las pantallas, con historial de navegación, efectos ejecutados FUERA del reducer y restauración RAII. Los loops individuales de F2 (sessions::run / actions::run) se consolidan acá; las pantallas solo renderizan.  Reglas: - el runtime recarga el snapshot de la pantalla ACTUAL en cada tick (mismo comportamiento que el oráculo: tiempos relativos frescos); - las acciones del motor se ejecutan en un thread (feedback en vivo, spinner por tick; F3 async pleno puede reemplazar el thread); - el detalle de sesión se carga por efecto (`LoadSessionDetail`).

## Relaciones

### Recibe de

- `use crate::actions`
- `use crate::app::state::{AppState, LoadState, Screen}`
- `use crate::app::{update as reducer, Action, Effect}`
- `use crate::keymap::{key_to_action, KeyContext}`
- `use crate::sessions`
- `use crate::terminal::{terminal_size, Tui}`
- `use crate::theme::{StatusKind, Theme}`
- `use crate::{home, lang, session_detail}`
- `use cortex_actions::context::ActionContext`
- `use cortex_actions::models::ActionResult`
- `use cortex_actions::registry::Registry`
- `use cortex_actions::runner::Runner`
- `use cortex_app::session::service::SessionService`
- `use cortex_app::session::{SessionStatus, SessionStorage}`
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/app/runtime.rs`.
