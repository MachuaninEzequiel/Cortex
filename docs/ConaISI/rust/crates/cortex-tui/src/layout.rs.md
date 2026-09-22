# rust/crates/cortex-tui/src/layout.rs

## Qué tiene adentro

Modos de layout del área disponible (spec §9).  Un solo punto de decisión de breakpoints para las pantallas operativas; el modo se DERIVA del área en cada render — nunca se guarda como estado mutable independiente. La variante del isotipo (prompt §18, `branding_mode`) sigue siendo la función de marca del logo; acá vive el mapeo pantalla→logo del rediseño (spec §8: Compact en cabeceras amplias, Mark en medianas/angostas, texto "CORTEX" bajo el ancho mínimo del Mark).
Archivo de 155 líneas.
Símbolos públicos observados:
- `pub enum LayoutMode`
- `pub fn layout_mode(area: Rect) -> LayoutMode`
- `pub fn logo_for(mode: LayoutMode, area_width: u16) -> Option<LogoVariant>`
- `pub fn render_too_small(f: &mut Frame<'_>, lang: &'static str)`
Tests en el mismo archivo: `umbrales_de_modo`, `logo_variante_por_modo_y_ancho`

## Para qué sirve

Modos de layout del área disponible (spec §9).  Un solo punto de decisión de breakpoints para las pantallas operativas; el modo se DERIVA del área en cada render — nunca se guarda como estado mutable independiente. La variante del isotipo (prompt §18, `branding_mode`) sigue siendo la función de marca del logo; acá vive el mapeo pantalla→logo del rediseño (spec §8: Compact en cabeceras amplias, Mark en medianas/angostas, texto "CORTEX" bajo el ancho mínimo del Mark).

## Relaciones

### Recibe de

- `use crate::renderer::CortexLogo`
- `use crate::theme::{self, Theme}`
- `use cortex_branding::logo::LogoVariant`
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/layout.rs`.
