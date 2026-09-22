# rust/crates/cortex-tui/src/components/help.rs

## Qué tiene adentro

Overlay de ayuda (spec §12): derivada del KeyMap, nunca texto hardcodeado por pantalla. Se dibuja al final (última capa).
Archivo de 45 líneas.
Símbolos públicos observados:
- `pub fn render_help(f: &mut Frame<'_>, area: Rect, theme: &Theme, lang: &'static str)`

## Para qué sirve

Overlay de ayuda (spec §12): derivada del KeyMap, nunca texto hardcodeado por pantalla. Se dibuja al final (última capa).

## Relaciones

### Recibe de

- `use crate::components::panel::draw_panel`
- `use crate::keymap::full_help`
- `use crate::theme::Theme`
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/components/help.rs`.
