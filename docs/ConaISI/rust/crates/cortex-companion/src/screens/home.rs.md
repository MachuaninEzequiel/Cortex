# rust/crates/cortex-companion/src/screens/home.rs

## Qué tiene adentro

Pantalla Home del Companion (G-B2b): sesión activa, próxima acción, doctor-lite y conteos de memoria sobre la identidad `cortex-branding`.  El Home es snapshot barato (gate P10 <50ms): render puro sobre `HomeData` que el binario carga de los backends. El render NUNCA muta estado.
Archivo de 542 líneas.
Símbolos públicos observados:
- `pub struct HomeData`
- `pub struct HomeAreas`
- `pub fn home_areas(area: Rect) -> HomeAreas`
- `pub struct AppRenderInfo`
- `pub struct BrandAssets`
- `pub fn render_home(`

## Para qué sirve

Pantalla Home del Companion (G-B2b): sesión activa, próxima acción, doctor-lite y conteos de memoria sobre la identidad `cortex-branding`.  El Home es snapshot barato (gate P10 <50ms): render puro sobre `HomeData` que el binario carga de los backends. El render NUNCA muta estado.

## Relaciones

### Recibe de

- `use cortex_branding::gradient::color_for`
- `use cortex_branding::logo`
- `use cortex_branding::pixels::PixelKind`
- `use crate::hud_brand`
- `use cortex_branding::Rgb`
- `use crate::app::{`
- `use crate::engine::{ActionProposal, DoctorSummary, SessionSummary, StatsSummary}`
- `use crate::widgets::{accent, button, panel, to_color, Button, Panel}`
- Contexto de crate `cortex-companion`: cortex-cli, cortex-actions, cortex-app, cortex-config, cortex-workspace, cortex-branding, cortex-brain, herdr CLI

### Envía a

- Crate `cortex-companion` envía hacia: TUI ratatui, action_log.jsonl, panes herdr

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/src/screens/home.rs`.
