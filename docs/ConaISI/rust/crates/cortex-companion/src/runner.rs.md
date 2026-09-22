# rust/crates/cortex-companion/src/runner.rs

## Qué tiene adentro

Runner común para cortex-companion y sus modos Herdr (Sidecar, Float, Co-Pilot).
Archivo de 322 líneas.
Símbolos públicos observados:
- `pub fn run_app(mode: CompanionMode, root: PathBuf, model: Option<String>)`

## Para qué sirve

Runner común para cortex-companion y sus modos Herdr (Sidecar, Float, Co-Pilot).

## Relaciones

### Recibe de

- `use crate::app::{self, AppAction, AppState}`
- `use crate::approval::ActionLog`
- `use crate::effects`
- `use crate::engine::{Backend, InProcessBackend}`
- `use crate::herdr`
- `use crate::screens::home::{home_areas, render_home, BrandAssets, HomeData}`
- `use crate::screens::menu_screen::{menu_areas, render_menu}`
- `use crate::screens::sessions_screen::{render_sessions, sessions_areas}`
- `use crate::screens::{`
- `use crate::{CompanionMode, Screen, UiRequest}`
- Contexto de crate `cortex-companion`: cortex-cli, cortex-actions, cortex-app, cortex-config, cortex-workspace, cortex-branding, cortex-brain, herdr CLI

### Envía a

- Crate `cortex-companion` envía hacia: TUI ratatui, action_log.jsonl, panes herdr

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/src/runner.rs`.
