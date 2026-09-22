# rust/crates/cortex-tui/src/app/mod.rs

## Qué tiene adentro

Capa `app` del crate (spec §2/§5): estado + acciones semánticas + reducer puro + efectos. El render nunca inicia procesos ni muta el dominio; el runtime ejecuta los efectos y devuelve acciones tipadas.  En F2 la única pantalla operativa es Sesiones; el `AppState` ya tiene la forma final (screen, overlay, foco, selección con scroll, notifs, should_quit) para que F4 agregue Home/Acciones/Búsqueda sin reescribir.
Archivo de 21 líneas.
Símbolos públicos observados:
- `pub mod action`
- `pub mod effect`
- `pub mod runtime`
- `pub mod search`
- `pub mod state`
- `pub mod update`
- `pub use action::Action`
- `pub use effect::Effect`
- `pub use runtime::`
- `pub use search::`
- `pub use state::`
- `pub use update::`

## Para qué sirve

Capa `app` del crate (spec §2/§5): estado + acciones semánticas + reducer puro + efectos. El render nunca inicia procesos ni muta el dominio; el runtime ejecuta los efectos y devuelve acciones tipadas.  En F2 la única pantalla operativa es Sesiones; el `AppState` ya tiene la forma final (screen, overlay, foco, selección con scroll, notifs, should_quit) para que F4 agregue Home/Acciones/Búsqueda sin reescribir.

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/app/mod.rs`.
