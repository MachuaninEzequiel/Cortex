# rust/crates/cortex-companion/src/app.rs

## Qué tiene adentro

Máquina ELM-lite de la app (G-B2a): estado + acciones semánticas + reducer puro + efectos, e input mouse-first con teclado dual.  El render NUNCA muta estado: la UI reduce `AppAction` vía `update` y solo produce un `Effect` opcional que el runtime (binario) aplica. El hit-test es puro: `rects` registradas + coordenadas del click ⇒ `AppAction`.
Archivo de 926 líneas.
Símbolos públicos observados:
- `pub use crate::hud_brand::MarkRam`
- `pub const LIQUID_IDLE_SECS: u64 = 90`
- `pub struct LiquidRam`
- `pub const HOME_SESSIONS_BTN: Rect = Rect::new(2, 4, 18, 3)`
- `pub const HOME_ACTIONS_BTN: Rect = Rect::new(24, 4, 18, 3)`
- `pub const HOME_OPEN_SESSION_BTN: Rect = Rect::new(46, 4, 18, 3)`
- `pub const HOME_MENU_BTN: Rect = Rect::new(66, 4, 12, 3)`
- `pub const MENU_LIST_LEFT: u16 = 2`
- `pub const MENU_LIST_TOP: u16 = 4`
- `pub const MENU_LIST_WIDTH: u16 = 56`
- `pub const MENU_LIST_HEIGHT: u16 = 16`
- `pub const MENU_OUTPUT_TOP: u16 = 20`
- `pub const MENU_OUTPUT_HEIGHT: u16 = 3`
- `pub const MENU_BACK_BTN: Rect = Rect::new(58, 1, 20, 3)`
- `pub const MODAL_RECT: Rect = Rect::new(10, 8, 60, 7)`
- `pub const MODAL_APROBAR_RECT: Rect = Rect::new(22, 12, 14, 2)`
- `pub const MODAL_DENEGAR_RECT: Rect = Rect::new(44, 12, 14, 2)`
- `pub const SESSIONS_LIST_LEFT: u16 = 2`
- `pub const SESSIONS_LIST_TOP: u16 = 4`
- `pub const SESSIONS_LIST_WIDTH: u16 = 76`
- … y 10 más en el extracto

## Para qué sirve

Máquina ELM-lite de la app (G-B2a): estado + acciones semánticas + reducer puro + efectos, e input mouse-first con teclado dual.  El render NUNCA muta estado: la UI reduce `AppAction` vía `update` y solo produce un `Effect` opcional que el runtime (binario) aplica. El hit-test es puro: `rects` registradas + coordenadas del click ⇒ `AppAction`.

## Relaciones

### Recibe de

- `use crate::approval::ApprovalRequest`
- `use crate::engine::{ActionProposal, SessionSummary}`
- `use crate::menu::{self, MenuOutput}`
- `use crate::{CompanionMode, Screen, UiRequest}`
- Contexto de crate `cortex-companion`: cortex-cli, cortex-actions, cortex-app, cortex-config, cortex-workspace, cortex-branding, cortex-brain, herdr CLI

### Envía a

- Crate `cortex-companion` envía hacia: TUI ratatui, action_log.jsonl, panes herdr

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/src/app.rs`.
