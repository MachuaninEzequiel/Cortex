# rust/crates/cortex-companion/tests/screens_snapshot.rs

## Qué tiene adentro

Archivo de 166 líneas.
Snapshots y presupuesto del render Home (G-B2b): render a Buffer sin terminal real (TestBackend de ratatui), hit-test coherente con las consts de `app.rs`, y presupuesto <50 ms (gate P10 pattern). Renderiza el Home a un Buffer 80x24 y devuelve (texto, info del render).
Tests: `home_renders_buttons_wordmark_and_budget`, `home_with_session_hides_open_button_and_shows_id`, `home_surfaces_load_error_p6p9`, `home_areas_use_same_consts_as_hit_test`, `home_doctor_fail_visible`

## Para qué sirve

Snapshots y presupuesto del render Home (G-B2b): render a Buffer sin terminal real (TestBackend de ratatui), hit-test coherente con las consts de `app.rs`, y presupuesto <50 ms (gate P10 pattern). Renderiza el Home a un Buffer 80x24 y devuelve (texto, info del render).

## Relaciones

### Recibe de

- `use cortex_companion::app::{HOME_ACTIONS_BTN, HOME_SESSIONS_BTN}`
- `use cortex_companion::engine::{ActionProposal, DoctorSummary, SessionSummary, StatsSummary}`
- `use cortex_companion::screens::home::{`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/tests/screens_snapshot.rs`. 166 líneas.
