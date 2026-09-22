# rust/crates/cortex-companion/examples/preview_ansi.rs

## Qué tiene adentro

Archivo de 118 líneas.
Preview visual de los modos de Herdr sin terminal: renderiza cada modo a un `TestBackend` y vuelca el buffer con los ESTILOS REALES de cada celda (fg/bg/símbolo) en un formato JSON compacto que el script de conversión a PNG consume. Uso:  cargo run -p cortex-companion --example preview_ansi -- <float|sidecar|copilot|home> \ > /tmp/preview.json  Es una herramienta de desarrollo (verificación de estética), no shipped.

## Para qué sirve

Preview visual de los modos de Herdr sin terminal: renderiza cada modo a un `TestBackend` y vuelca el buffer con los ESTILOS REALES de cada celda (fg/bg/símbolo) en un formato JSON compacto que el script de conversión a PNG consume. Uso:  cargo run -p cortex-companion --example preview_ansi -- <float|sidecar|copilot|home> \ > /tmp/preview.json  Es una herramienta de desarrollo (verificación de estética), no shipped.

## Relaciones

### Recibe de

- `use cortex_companion::engine::{ActionProposal, DoctorSummary, SessionSummary, StatsSummary}`
- `use cortex_companion::screens::copilot_screen::{copilot_areas, render_copilot}`
- `use cortex_companion::screens::home::{home_areas, render_home, BrandAssets, HomeData}`
- `use cortex_companion::screens::hud_screen::{hud_areas, render_hud}`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/examples/preview_ansi.rs`. 118 líneas.
