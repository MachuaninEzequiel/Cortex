# rust/crates/cortex-companion/tests/menu_catalog.rs

## Qué tiene adentro

Archivo de 318 líneas.
Tests de integración del Menu (G-B2c): catálogo de 27 familias, render a buffer sin terminal real, hit-test de entradas/scroll y ejecución in-process del engine (paridad + honestidad P6/P9). Renderiza el Menu 80x24 a (texto, botones registrados, ms).
Tests: `catalog_has_all_27_families_grouped`, `menu_entry_mutation_requires_approval_flow`, `menu_render_shows_domains_entries_and_budget`, `menu_output_panel_shows_result_and_error`, `menu_click_entry_runs_command`, `menu_click_header_row_is_noop`, `menu_click_output_panel_is_noop`, `menu_click_last_visible_row_runs_command`, `menu_back_button_goes_back`, `menu_scroll_reveals_lower_entries`, `home_menu_button_navigates_to_menu`, `menu_run_integrated_families_produce_output`, `menu_run_unintegrated_fails_explicit_p6p9`

## Para qué sirve

Tests de integración del Menu (G-B2c): catálogo de 27 familias, render a buffer sin terminal real, hit-test de entradas/scroll y ejecución in-process del engine (paridad + honestidad P6/P9). Renderiza el Menu 80x24 a (texto, botones registrados, ms).

## Relaciones

### Recibe de

- `use cortex_companion::app::{`
- `use cortex_companion::engine::{Backend, InProcessBackend}`
- `use cortex_companion::menu::{`
- `use cortex_companion::screens::menu_screen::{menu_areas, render_menu}`
- `use cortex_companion::{Screen, UiRequest}`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/tests/menu_catalog.rs`. 318 líneas.
