# rust/crates/cortex-companion/tests/hud.rs

## Qué tiene adentro

Archivo de 285 líneas.
HUD v1 (doc 17): layout, hit-test, Copiar, Esc sale, sin inyectar.
Tests: `hygiene_filter_rejects_session_lifecycle`, `hud_render_has_copy_not_dashboard`, `hud_brand_column_matches_grid`, `hud_copy_click_emits_copy_prompt`, `hud_esc_quits`, `hud_approve_opens_modal_for_hygiene`, `hud_skip_remembers_hygiene_id`, `hud_skip_escribe_actions_yaml`, `enter_without_ask_copies_not_injects`, `prompt_plan_pide_implement_al_agente`, `prompt_sin_fase_pide_checkpoint_al_agente`, `prompt_sin_sesion_pide_skills_no_cli`, `prompt_nunca_menciona_cortex_session`, `liquid_ram_transition_idle_weak_awake`, `hud_sidecar_40x24_renders_vertical_layout`

## Para qué sirve

HUD v1 (doc 17): layout, hit-test, Copiar, Esc sale, sin inyectar.

## Relaciones

### Recibe de

- `use cortex_companion::app::{hit_test, update, AppAction, AppState, Effect}`
- `use cortex_companion::engine::ActionProposal`
- `use cortex_companion::screens::home::HomeData`
- `use cortex_companion::screens::hud_screen::{hud_areas, hud_prompt, is_hygiene, render_hud}`
- `use cortex_companion::{CompanionMode, Screen, UiRequest}`
- `use cortex_companion::app::{LiquidRam, MarkRam}`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/tests/hud.rs`. 285 líneas.
