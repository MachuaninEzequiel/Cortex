# rust/crates/cortex-companion/src/screens/hud_screen.rs

## Qué tiene adentro

HUD v1 (doc 17): columna de marca en celdas + diálogos. Sin placa, sin cajas de navegación, sin inyectar al agente.
Archivo de 455 líneas.
Símbolos públicos observados:
- `pub fn is_hygiene(id: &str) -> bool`
- `pub fn pick_hygiene<'a>(`
- `pub const PROMPT_NO_SESSION: &str = "no hay sesión activa. abrí el trabajo con las skills de Cortex (grill / to-spec / sesión). no pidas que el humano corra la CLI."`
- `pub const PROMPT_NO_PHASE: &str = "checkpoint de lo que acabás de hacer: evidencia, artifacts tocados, nota de una línea. dirigido a vos, no un comando para el humano."`
- `pub const PROMPT_NEXT_SPEC: &str = "el requisito ya está grillado. escribí una spec con Goal medible, Non-goals, Acceptance criteria SI/NO, files_in_scope y verification hooks. per`
- `pub const PROMPT_NEXT_PLAN: &str = "la spec está. ticketizá en vertical slices: What, Blocked by, Verification, Done when. persistí `.scratch/<feature>/issues/NN-slug.md`. no le pi`
- `pub const PROMPT_NEXT_IMPLEMENT: &str = "tomá el siguiente ticket desbloqueado e implementalo respetando files_in_scope de la spec`
- `pub const PROMPT_NEXT_REVIEW: &str = "revisá en dos ejes (Standards y Spec) con hallazgos file:line. veredicto approve / request-changes / block. no le pidas al humano `cortex revi`
- `pub const PROMPT_NEXT_CLOSE: &str = "el trabajo está en review. cerrá la sesión con las skills/MCP de Cortex (documenter COMPOSED, tool cortex_finish_session). no le pidas al human`
- `pub const PROMPT_PHASE_CLOSE: &str = "la sesión ya está en close. no empujes más fase. si falta evidencia, documentala`
- `pub fn compose_agent_prompt(session: Option<&crate::engine::SessionSummary>) -> String`
- `pub fn hud_prompt(data: &HomeData) -> String`
- `pub struct HudAreas`
- `pub fn hud_areas(area: Rect) -> HudAreas`
- `pub fn hud_hit_test(`
- `pub fn render_hud(`

## Para qué sirve

HUD v1 (doc 17): columna de marca en celdas + diálogos. Sin placa, sin cajas de navegación, sin inyectar al agente.

## Relaciones

### Recibe de

- `use crate::app::AppAction`
- `use crate::engine::ActionProposal`
- `use crate::hud_brand`
- `use crate::screens::home::{AppRenderInfo, HomeData}`
- `use crate::widgets::{to_color, Button}`
- `use cortex_branding::Rgb`
- Contexto de crate `cortex-companion`: cortex-cli, cortex-actions, cortex-app, cortex-config, cortex-workspace, cortex-branding, cortex-brain, herdr CLI

### Envía a

- Crate `cortex-companion` envía hacia: TUI ratatui, action_log.jsonl, panes herdr

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/src/screens/hud_screen.rs`.
