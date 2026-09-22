# rust/crates/cortex-tui/tests/snapshots.rs

## Qué tiene adentro

Archivo de 392 líneas.
Snapshots de render con TestBackend (prompt-logo.md §45 + rediseño F2): Full/Compact/Minimal sin panic, sin escritura fuera del área, variante correcta según breakpoint, determinismo, gate de latencia del Home (<50ms), y los snapshots de tamaño del rediseño (spec §16.3): 160×45 / 100×30 / 80×24 / 68×20 / 40×12 / TooSmall, invariantes 1×1..200×80 y reloj inyectado en los tiempos relativos.
Tests: `splash_full_en_pantalla_grande`, `splash_compact_en_pantalla_mediana`, `splash_minimal_en_pantalla_chica`, `splash_no_explode_en_area_minima`, `home_renderiza_estado_demo`, `home_es_determinista`, `home_no_pinta_fuera_del_area`, `home_render_bajo_presupuesto_50ms`, `sesiones_wide_160x45`, `sesiones_standard_100x30`, `sesiones_compact_80x24`, `sesiones_minimo_68x20`, `sesiones_minimal_40x12`, `sesiones_too_small_estable`, `sesiones_vacias_estado_explicito`, `sesiones_failed_estado_explicito`, `sesiones_loading_estado_explicito`, `ayuda_se_abre_como_overlay`, `render_determinista_del_mismo_snapshot`, `seleccion_mueve_la_barra_y_la_posicion`

## Para qué sirve

Snapshots de render con TestBackend (prompt-logo.md §45 + rediseño F2): Full/Compact/Minimal sin panic, sin escritura fuera del área, variante correcta según breakpoint, determinismo, gate de latencia del Home (<50ms), y los snapshots de tamaño del rediseño (spec §16.3): 160×45 / 100×30 / 80×24 / 68×20 / 40×12 / TooSmall, invariantes 1×1..200×80 y reloj inyectado en los tiempos relativos.

## Relaciones

### Recibe de

- `use cortex_tui::app::{update as reducer, Action, AppState, LoadState}`
- `use cortex_tui::sessions::{rel_time, SessionRow, SessionsScreenData}`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/tests/snapshots.rs`. 392 líneas.
