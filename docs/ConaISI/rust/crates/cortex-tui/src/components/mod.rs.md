# rust/crates/cortex-tui/src/components/mod.rs

## Qué tiene adentro

Componentes visuales base del rediseño (spec §13): cada componente se dibuja en su módulo; `ui.rs` compone (acá: las pantallas).
Archivo de 52 líneas.
Símbolos públicos observados:
- `pub mod empty_state`
- `pub mod feedback`
- `pub mod header`
- `pub mod help`
- `pub mod list`
- `pub mod panel`
- `pub mod status_bar`
- `pub fn truncate_visual(s: &str, max: usize) -> String`
Tests en el mismo archivo: `truncado_por_ancho_visual`, `truncado_unicode_seguro`

## Para qué sirve

Componentes visuales base del rediseño (spec §13): cada componente se dibuja en su módulo; `ui.rs` compone (acá: las pantallas).

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/components/mod.rs`.
