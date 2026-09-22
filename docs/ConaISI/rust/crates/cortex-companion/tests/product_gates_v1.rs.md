# rust/crates/cortex-companion/tests/product_gates_v1.rs

## Qué tiene adentro

Archivo de 246 líneas.
Gates v1 del Producto 17 §14.  Verifica el paquete completo de aceptación: HUD default, Copiar con OSC 52, higiene filtrada, idle ≠ awake, layout adaptativo, y cero bypass.
Tests: `gate_1_manifest_open_es_float_no_sidecar`, `gate_2_send_text_no_se_llama_desde_companion_productivo`, `gate_2_enter_vacio_copia_prompt`, `gate_3_pick_hygiene_ignora_close_y_checkpoint`, `gate_4_mark_idle_distinto_de_awake`, `gate_5_snapshot_hud_sin_dashboard`, `gate_6_prompt_nunca_pide_al_humano_correr_cli`, `gate_7_runner_no_abre_llama_antes_del_loop`, `gate_8_conclude_spawn_honestidad`, `gate_9_sidecar_40x24_renders_vertical_layout`

## Para qué sirve

Gates v1 del Producto 17 §14.  Verifica el paquete completo de aceptación: HUD default, Copiar con OSC 52, higiene filtrada, idle ≠ awake, layout adaptativo, y cero bypass.

## Relaciones

### Recibe de

- `use cortex_companion::app::{update, AppAction, AppState, Effect, MarkRam}`
- `use cortex_companion::engine::ActionProposal`
- `use cortex_companion::herdr::{conclude_spawn, SpawnKind}`
- `use cortex_companion::hud_brand::{blit_mark, tone, TOP}`
- `use cortex_companion::screens::home::HomeData`
- `use cortex_companion::screens::hud_screen::{`
- `use cortex_companion::{CompanionMode, Screen, UiRequest}`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/tests/product_gates_v1.rs`. 246 líneas.
