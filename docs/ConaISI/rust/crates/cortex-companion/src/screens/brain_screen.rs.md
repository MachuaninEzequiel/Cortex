# rust/crates/cortex-companion/src/screens/brain_screen.rs

## Qué tiene adentro

Pantalla Brain del Companion (G-B4): chat con el agente local.  Muestra el historial (usuario/brain/propuestas), el input con cursor y el botón [Ejecutar] por propuesta. La geometría es COMPARTIDA con `hit_test` (consts de `app.rs`); presupuesto de render <50 ms (patrón P10). El render NUNCA muta estado ni ejecuta nada: las propuestas se resuelven por la máquina de estados (modal → `run_guarded`).
Archivo de 224 líneas.
Símbolos públicos observados:
- `pub struct BrainAreas`
- `pub fn brain_areas(_area: Rect) -> BrainAreas`
- `pub enum BrainRow`
- `pub fn brain_rows(panel: &BrainPanel) -> Vec<BrainRow>`
- `pub struct BrainRenderInfo`
- `pub fn render_brain(`

## Para qué sirve

Pantalla Brain del Companion (G-B4): chat con el agente local.  Muestra el historial (usuario/brain/propuestas), el input con cursor y el botón [Ejecutar] por propuesta. La geometría es COMPARTIDA con `hit_test` (consts de `app.rs`); presupuesto de render <50 ms (patrón P10). El render NUNCA muta estado ni ejecuta nada: las propuestas se resuelven por la máquina de estados (modal → `run_guarded`).

## Relaciones

### Recibe de

- `use crate::app::{`
- `use crate::brain_panel::{BrainMode, BrainPanel}`
- Contexto de crate `cortex-companion`: cortex-cli, cortex-actions, cortex-app, cortex-config, cortex-workspace, cortex-branding, cortex-brain, herdr CLI

### Envía a

- Crate `cortex-companion` envía hacia: TUI ratatui, action_log.jsonl, panes herdr

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/src/screens/brain_screen.rs`.
