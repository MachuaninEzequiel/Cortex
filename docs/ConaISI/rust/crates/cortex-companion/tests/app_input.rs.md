# rust/crates/cortex-companion/tests/app_input.rs

## Qué tiene adentro

Archivo de 203 líneas.
Tests de la máquina de estado (G-B2a): AppAction / AppState / update / hit_test / translate_event — mouse-first + teclado dual, sin terminal real.
Tests: `mouse_click_on_nav_screen_navigates`, `click_outside_any_area_is_none`, `scroll_down_translates_to_scroll_down`, `scroll_up_translates_to_scroll_up`, `mouse_left_click_translates_to_click_with_coords`, `keyboard_esc_equivalent_to_back`, `keyboard_q_equivalent_to_quit`, `q_in_search_types_into_query_and_never_quits`, `q_outside_search_still_quits`, `ctrl_c_quits_even_from_search`, `typed_char_passes_through`, `enter_maps_to_key_for_future_focus_activation`, `quit_sets_quit_flag`, `run_command_declares_effect`, `scroll_on_empty_state_is_noop`, `home_button_contains_its_center`, `back_on_empty_stack_is_noop`

## Para qué sirve

Tests de la máquina de estado (G-B2a): AppAction / AppState / update / hit_test / translate_event — mouse-first + teclado dual, sin terminal real.

## Relaciones

### Recibe de

- `use cortex_companion::app::{`
- `use cortex_companion::{Screen, UiRequest}`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/tests/app_input.rs`. 203 líneas.
