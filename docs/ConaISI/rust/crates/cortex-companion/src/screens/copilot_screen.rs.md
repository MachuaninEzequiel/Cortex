# rust/crates/cortex-companion/src/screens/copilot_screen.rs

## Qué tiene adentro

Pantalla Co-Pilot Dual (Opción 3) — interacción en vivo con el agente adyacente.
Archivo de 376 líneas.
Símbolos públicos observados:
- `pub struct CopilotAreas`
- `pub fn copilot_areas(area: Rect) -> CopilotAreas`
- `pub fn render_copilot(`

## Para qué sirve

Pantalla Co-Pilot Dual (Opción 3) — interacción en vivo con el agente adyacente.

## Relaciones

### Recibe de

- `use crate::herdr::HerdrAgentInfo`
- `use crate::screens::home::{AppRenderInfo, HomeData}`
- `use crate::widgets::{button, panel, to_color, Button, Panel}`
- `use cortex_branding::logo`
- `use cortex_branding::palette::{CYAN, DEEP, ICE, LIGHT, SHADOW}`
- `use cortex_branding::pixels::PixelKind`
- `use cortex_branding::Rgb`
- Contexto de crate `cortex-companion`: cortex-cli, cortex-actions, cortex-app, cortex-config, cortex-workspace, cortex-branding, cortex-brain, herdr CLI

### Envía a

- Crate `cortex-companion` envía hacia: TUI ratatui, action_log.jsonl, panes herdr

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/src/screens/copilot_screen.rs`.
