# rust/crates/cortex-companion/src/theme.rs

## Qué tiene adentro

Tema del Companion: los MISMOS tokens Catppuccin Mocha de `cortex-tui` (spec §3 del rediseño), resueltos vía el crate `catppuccin`.  Regla de higiene idéntica a la TUI: ningún `Color::Rgb(...)` de chrome fuera de `theme.rs` (los tokens fríos del wordmark viven en `cortex_branding::wordmark`). El verde menta de `cortex_branding::palette` queda SOLO para el isotipo del logo; todo el chrome usa mauve/sky/lavender.
Archivo de 49 líneas.
Símbolos públicos observados:
- `pub fn border_idle() -> Color`
- `pub fn border_focus() -> Color`
- `pub fn selection_bg() -> Color`

## Para qué sirve

Tema del Companion: los MISMOS tokens Catppuccin Mocha de `cortex-tui` (spec §3 del rediseño), resueltos vía el crate `catppuccin`.  Regla de higiene idéntica a la TUI: ningún `Color::Rgb(...)` de chrome fuera de `theme.rs` (los tokens fríos del wordmark viven en `cortex_branding::wordmark`). El verde menta de `cortex_branding::palette` queda SOLO para el isotipo del logo; todo el chrome usa mauve/sky/lavender.

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-companion`: cortex-cli, cortex-actions, cortex-app, cortex-config, cortex-workspace, cortex-branding, cortex-brain, herdr CLI

### Envía a

- Crate `cortex-companion` envía hacia: TUI ratatui, action_log.jsonl, panes herdr

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/src/theme.rs`.
