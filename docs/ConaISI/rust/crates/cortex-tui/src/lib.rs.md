# rust/crates/cortex-tui/src/lib.rs

## Qué tiene adentro

cortex-tui — TUI nativa de Cortex sobre ratatui (Obra 07 P10).  Identidad visual (`cortex-branding`) renderizada como `Widget` de ratatui, pantalla splash y layout del Home. El Home espeja la arquitectura de información de `cortex/tui/core.py` (HomeState) con datos demo: el cableado a servicios reales (sessions/acciones/vault) llega cuando cortex-app los exponga (P4-P6 del plan 08).  ```no_run use cortex_tui::{CortexLogo, LogoVariant}; use ratatui::Frame;
Archivo de 133 líneas.
Símbolos públicos observados:
- `pub mod actions`
- `pub mod app`
- `pub mod clipboard`
- `pub mod components`
- `pub mod deprecated`
- `pub mod event`
- `pub mod hit`
- `pub mod home`
- `pub mod keymap`
- `pub mod layout`
- `pub mod renderer`
- `pub mod search`
- `pub mod session_detail`
- `pub mod sessions`
- `pub mod splash`
- `pub mod terminal`
- `pub mod theme`
- `pub mod view`
- `pub use actions::`
- `pub use clipboard::copy_to_clipboard`
- … y 10 más en el extracto
Tests en el mismo archivo: `breakpoints_del_prompt`, `modo_mapea_a_variante`

## Para qué sirve

cortex-tui — TUI nativa de Cortex sobre ratatui (Obra 07 P10).  Identidad visual (`cortex-branding`) renderizada como `Widget` de ratatui, pantalla splash y layout del Home. El Home espeja la arquitectura de información de `cortex/tui/core.py` (HomeState) con datos demo: el cableado a servicios reales (sessions/acciones/vault) llega cuando cortex-app los exponga (P4-P6 del plan 08).  ```no_run use cortex_tui::{CortexLogo, LogoVariant}; use ratatui::Frame;

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/lib.rs`.
