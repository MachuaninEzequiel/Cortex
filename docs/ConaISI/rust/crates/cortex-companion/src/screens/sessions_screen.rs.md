# rust/crates/cortex-companion/src/screens/sessions_screen.rs

## Qué tiene adentro

Pantalla Sessions del Companion (G-B3 UI): lista en vivo de sesiones, click en fila ⇒ detalle (checkpoints/tasks), y [Cerrar sesión] que SIEMPRE pasa por el modal de aprobación (`run_guarded`, B2). El render es puro sobre `SessionsData`; la carga de datos la hace el runtime.  Geometría COMPARTIDA con `hit_test` (consts de `app.rs`): render y hit-test no pueden divergir.
Archivo de 213 líneas.
Símbolos públicos observados:
- `pub struct SessionsAreas`
- `pub fn sessions_areas(_area: Rect) -> SessionsAreas`
- `pub struct SessionsRenderInfo`
- `pub fn render_sessions(`

## Para qué sirve

Pantalla Sessions del Companion (G-B3 UI): lista en vivo de sesiones, click en fila ⇒ detalle (checkpoints/tasks), y [Cerrar sesión] que SIEMPRE pasa por el modal de aprobación (`run_guarded`, B2). El render es puro sobre `SessionsData`; la carga de datos la hace el runtime.  Geometría COMPARTIDA con `hit_test` (consts de `app.rs`): render y hit-test no pueden divergir.

## Relaciones

### Recibe de

- `use crate::app::{`
- `use crate::widgets::{button, Button}`
- Contexto de crate `cortex-companion`: cortex-cli, cortex-actions, cortex-app, cortex-config, cortex-workspace, cortex-branding, cortex-brain, herdr CLI

### Envía a

- Crate `cortex-companion` envía hacia: TUI ratatui, action_log.jsonl, panes herdr

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/src/screens/sessions_screen.rs`.
