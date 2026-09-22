# rust/crates/cortex-companion/src/screens/actions_screen.rs

## Qué tiene adentro

Pantalla Actions del Companion (G-B3 UI): propuestas del Action Engine con score/costo/reversibilidad; [Aprobar] por acción y [Aprobar lote auto-ok] (solo reversibles de costo instant) — TODO pasa por el modal de la máquina de estados (`run_guarded`, B2), con auditoría por ítem.  Geometría COMPARTIDA con `hit_test` (consts de `app.rs`).
Archivo de 215 líneas.
Símbolos públicos observados:
- `pub struct ActionsAreas`
- `pub fn actions_areas(_area: Rect) -> ActionsAreas`
- `pub struct ActionsRenderInfo`
- `pub fn render_actions(`

## Para qué sirve

Pantalla Actions del Companion (G-B3 UI): propuestas del Action Engine con score/costo/reversibilidad; [Aprobar] por acción y [Aprobar lote auto-ok] (solo reversibles de costo instant) — TODO pasa por el modal de la máquina de estados (`run_guarded`, B2), con auditoría por ítem.  Geometría COMPARTIDA con `hit_test` (consts de `app.rs`).

## Relaciones

### Recibe de

- `use crate::app::{`
- `use crate::engine::ActionProposal`
- `use crate::widgets::{button, Button}`
- Contexto de crate `cortex-companion`: cortex-cli, cortex-actions, cortex-app, cortex-config, cortex-workspace, cortex-branding, cortex-brain, herdr CLI

### Envía a

- Crate `cortex-companion` envía hacia: TUI ratatui, action_log.jsonl, panes herdr

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/src/screens/actions_screen.rs`.
