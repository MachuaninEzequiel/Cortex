# rust/crates/cortex-companion/src/screens/search_screen.rs

## Qué tiene adentro

Pantalla Search del Companion (G-B2d): input por teclado + hits de la MISMA pipeline híbrida que el CLI (vía `Backend::search`, top-k 5) + botón [Útil] por hit episódico que persiste feedback en `.cortex/feedback.jsonl` (formato del oráculo, `crate::feedback`).  Geometría COMPARTIDA con `hit_test` (consts de `app.rs`), presupuesto de render <50 ms (patrón P10), y salida de feedback visible (nunca silencio).
Archivo de 236 líneas.
Símbolos públicos observados:
- `pub struct SearchData`
- `pub struct SearchAreas`
- `pub fn search_areas(_area: Rect) -> SearchAreas`
- `pub struct SearchRenderInfo`
- `pub fn render_search(`

## Para qué sirve

Pantalla Search del Companion (G-B2d): input por teclado + hits de la MISMA pipeline híbrida que el CLI (vía `Backend::search`, top-k 5) + botón [Útil] por hit episódico que persiste feedback en `.cortex/feedback.jsonl` (formato del oráculo, `crate::feedback`).  Geometría COMPARTIDA con `hit_test` (consts de `app.rs`), presupuesto de render <50 ms (patrón P10), y salida de feedback visible (nunca silencio).

## Relaciones

### Recibe de

- `use crate::app::{`
- `use crate::engine::SearchHit`
- Contexto de crate `cortex-companion`: cortex-cli, cortex-actions, cortex-app, cortex-config, cortex-workspace, cortex-branding, cortex-brain, herdr CLI

### Envía a

- Crate `cortex-companion` envía hacia: TUI ratatui, action_log.jsonl, panes herdr

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/src/screens/search_screen.rs`.
