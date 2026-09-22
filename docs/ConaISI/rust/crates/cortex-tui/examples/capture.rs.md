# rust/crates/cortex-tui/examples/capture.rs

## Qué tiene adentro

Archivo de 171 líneas.
Captura headless ANSI truecolor de las pantallas (dev): vuelca el buffer EXACTO del render (símbolos + estilos) a stdout. Es la materia prima de `assets/shots/make_shots.py` para regenerar las imágenes del README con el diseño vigente, sin terminal real y determinista.  ```bash cargo run -p cortex-tui --example capture -- splash [--width 100] [--height 30] cargo run -p cortex-tui --example capture -- home cargo run -p cortex-tui --example capture -- sessions --project-root DIR [--select N] cargo run -p cortex-tui --example capture -- actions --project-root DIR [--confirm N] [--select N] ```

## Para qué sirve

Captura headless ANSI truecolor de las pantallas (dev): vuelca el buffer EXACTO del render (símbolos + estilos) a stdout. Es la materia prima de `assets/shots/make_shots.py` para regenerar las imágenes del README con el diseño vigente, sin terminal real y determinista.  ```bash cargo run -p cortex-tui --example capture -- splash [--width 100] [--height 30] cargo run -p cortex-tui --example capture -- home cargo run -p cortex-tui --example capture -- sessions --project-root DIR [--select N] cargo run -p cortex-tui --example capture -- actions --project-root DIR [--confirm N] [--select N] ```

## Relaciones

### Recibe de

- `use cortex_app::session::service::SessionService`
- `use cortex_app::session::SessionStorage`
- `use cortex_tui::app::{update as reducer, Action, AppState}`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/examples/capture.rs`. 171 líneas.
