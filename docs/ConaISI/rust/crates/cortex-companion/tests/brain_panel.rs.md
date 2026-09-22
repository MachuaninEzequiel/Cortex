# rust/crates/cortex-companion/tests/brain_panel.rs

## Qué tiene adentro

Archivo de 559 líneas.
B8 — Brain panel híbrido (G-B4, doc 14 §2.2/§2.3): - reads del brain enrutadas por el engine IN-PROCESS (nunca subprocess); - Tool::READ ejecuta directa, sin aprobación (aserción: sin `pending`, sin líneas de auditoría); - propuesta de MUTACIÓN (línea "cortex <familia> ..." guardada) ⇒ BrainMsg::Proposal con [Ejecutar] → run_guarded (aprobar ejecuta y audita; denegar NUNCA ejecuta); - tools no mapeadas / inexistentes ⇒ Err explícito con nombre (P6/P9); - router determinista: cero tokens, cero LLM, cero subprocess. Backend de test con contadores: registra cada lectura y cada `menu_run`.
Tests: `read_tool_executes_directly_no_approval`, `mutate_proposal_shows_execute_button_and_guards`, `read_commands_never_become_proposals`, `unmapped_tool_fails_explicitly`, `unknown_tool_fails_explicitly_with_name`, `unknown_tool_from_model_never_routes`, `deterministic_router_zero_tokens`, `deterministic_free_search_routes_to_engine`, `actions_propose_lists_and_its_effect_is_guarded_text`, `brain_input_types_q_and_slash_without_quitting`, `enter_emits_brain_turn_with_trim_and_clears_input`, `brain_turn_effect_appends_messages_deterministic`, `home_brain_button_navigates`, `brain_row_click_resolves_to_command`, `brain_screen_renders_chat_and_budget`, `tokenize_handles_quotes`

## Para qué sirve

B8 — Brain panel híbrido (G-B4, doc 14 §2.2/§2.3): - reads del brain enrutadas por el engine IN-PROCESS (nunca subprocess); - Tool::READ ejecuta directa, sin aprobación (aserción: sin `pending`, sin líneas de auditoría); - propuesta de MUTACIÓN (línea "cortex <familia> ..." guardada) ⇒ BrainMsg::Proposal con [Ejecutar] → run_guarded (aprobar ejecuta y audita; denegar NUNCA ejecuta); - tools no mapeadas / inexistentes ⇒ Err explícito con nombre (P6/P9); - router determinista: cero tokens, cero LLM, cero subprocess. Backend de test con contadores: registra cada lectura y cada `menu_run`.

## Relaciones

### Recibe de

- `use cortex_brain::chat::ScriptedBackend`
- `use cortex_companion::app::{`
- `use cortex_companion::approval::ActionLog`
- `use cortex_companion::brain_panel::{`
- `use cortex_companion::effects`
- `use cortex_companion::engine::{`
- `use cortex_companion::screens::{brain_areas, brain_rows, render_brain}`
- `use cortex_companion::{Screen, UiRequest}`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/tests/brain_panel.rs`. 559 líneas.
