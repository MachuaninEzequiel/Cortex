# rust/crates/cortex-companion/src/widgets.rs

## Qué tiene adentro

Widgets mínimos del Companion (G-B2b): Panel, Button y List con estados hover/active via borde.  Duplicación ACOTADA de widgets de cortex-tui (documento 14 §2.1): el Companion no depende de cortex-tui (WIP con goldens congelados). Refactor a reuso cuando el TUI se estabilice (post-cierre, fuera de alcance).
Archivo de 125 líneas.
Símbolos públicos observados:
- `pub(crate) fn to_color(c: palette::Rgb) -> Color`
- `pub(crate) fn accent() -> Color`
- `pub struct Button`
- `pub fn button(f: &mut Frame<'_>, b: &Button, hovered: bool)`
- `pub struct Panel`
- `pub fn panel(f: &mut Frame<'_>, p: &Panel, lines: Vec<Line<'_>>, title_color: Color)`
- `pub struct List`
- `pub fn list(f: &mut Frame<'_>, l: &List)`

## Para qué sirve

Widgets mínimos del Companion (G-B2b): Panel, Button y List con estados hover/active via borde.  Duplicación ACOTADA de widgets de cortex-tui (documento 14 §2.1): el Companion no depende de cortex-tui (WIP con goldens congelados). Refactor a reuso cuando el TUI se estabilice (post-cierre, fuera de alcance).

## Relaciones

### Recibe de

- `use crate::theme`
- `use cortex_branding::palette`
- Contexto de crate `cortex-companion`: cortex-cli, cortex-actions, cortex-app, cortex-config, cortex-workspace, cortex-branding, cortex-brain, herdr CLI

### Envía a

- Crate `cortex-companion` envía hacia: TUI ratatui, action_log.jsonl, panes herdr

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/src/widgets.rs`.
