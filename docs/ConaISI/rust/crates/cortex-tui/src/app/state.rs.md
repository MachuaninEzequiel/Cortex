# rust/crates/cortex-tui/src/app/state.rs

## Qué tiene adentro

Estado de la aplicación (spec §5): enums exhaustivos, sin combinaciones imposibles de booleanos; el render es función pura del estado.
Archivo de 218 líneas.
Símbolos públicos observados:
- `pub enum Screen`
- `pub enum SearchMode`
- `pub enum Overlay`
- `pub enum LoadState<T>`
- `pub struct Notification`
- `pub struct AppState`
Tests en el mismo archivo: `estado_nuevo_empieza_cargando`, `list_len_solo_con_datos`

## Para qué sirve

Estado de la aplicación (spec §5): enums exhaustivos, sin combinaciones imposibles de booleanos; el render es función pura del estado.

## Relaciones

### Recibe de

- `use crate::layout::LayoutMode`
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/app/state.rs`.
