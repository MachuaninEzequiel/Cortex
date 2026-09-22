# rust/crates/cortex-branding/src/lib.rs

## Qué tiene adentro

cortex-branding — identidad visual de Cortex, PURA (sin dependencias).  Traducción terminal-native del logo aprobado (`docs/logo/cortex-logo.png`, contrato estético en `docs/logo/prompt-logo.md`): half-block rendering, máscaras de píxeles separadas del gradiente, paleta monocromática azul/cyan fría. La integración como `Widget` de ratatui vive en `cortex-tui`; acá solo hay lógica de identidad reutilizable por cualquier binario (brain, cli, tui) sin arrastrar dependencias pesadas.  ```no_run use cortex_branding::{ansi, logo::LogoVariant};
Archivo de 25 líneas.
Símbolos públicos observados:
- `pub mod ansi`
- `pub mod gradient`
- `pub mod logo`
- `pub mod palette`
- `pub mod pixels`
- `pub mod wordmark`
- `pub use palette::Rgb`
- `pub use pixels::`

## Para qué sirve

cortex-branding — identidad visual de Cortex, PURA (sin dependencias).  Traducción terminal-native del logo aprobado (`docs/logo/cortex-logo.png`, contrato estético en `docs/logo/prompt-logo.md`): half-block rendering, máscaras de píxeles separadas del gradiente, paleta monocromática azul/cyan fría. La integración como `Widget` de ratatui vive en `cortex-tui`; acá solo hay lógica de identidad reutilizable por cualquier binario (brain, cli, tui) sin arrastrar dependencias pesadas.  ```no_run use cortex_branding::{ansi, logo::LogoVariant};

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-branding`: nada de otros crates Cortex

### Envía a

- Crate `cortex-branding` envía hacia: cortex-brain (banner), cortex-tui, cortex-companion

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-branding/src/lib.rs`.
