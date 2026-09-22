# rust/crates/cortex-companion/src/screens/mod.rs

## Qué tiene adentro

Pantallas del Companion (G-B2b+): cada una renderiza sobre datos puros y devuelve `AppRenderInfo` con los botones del frame (para el hit-test del siguiente). El binario inyecta los backends; los render no tocan I/O.
Archivo de 90 líneas.
Símbolos públicos observados:
- `pub mod actions_screen`
- `pub mod brain_screen`
- `pub mod copilot_screen`
- `pub mod home`
- `pub mod hud_screen`
- `pub mod menu_screen`
- `pub mod search_screen`
- `pub mod sessions_screen`
- `pub use actions_screen::`
- `pub use brain_screen::`
- `pub use copilot_screen::`
- `pub use home::`
- `pub use hud_screen::`
- `pub use menu_screen::`
- `pub use modal::render_modal`
- `pub use search_screen::`
- `pub use sessions_screen::`

## Para qué sirve

Pantallas del Companion (G-B2b+): cada una renderiza sobre datos puros y devuelve `AppRenderInfo` con los botones del frame (para el hit-test del siguiente). El binario inyecta los backends; los render no tocan I/O.

## Relaciones

### Recibe de

- `use crate::app::{MODAL_APROBAR_RECT, MODAL_DENEGAR_RECT, MODAL_RECT}`
- `use crate::approval::ApprovalRequest`
- Contexto de crate `cortex-companion`: cortex-cli, cortex-actions, cortex-app, cortex-config, cortex-workspace, cortex-branding, cortex-brain, herdr CLI

### Envía a

- Crate `cortex-companion` envía hacia: TUI ratatui, action_log.jsonl, panes herdr

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/src/screens/mod.rs`.
