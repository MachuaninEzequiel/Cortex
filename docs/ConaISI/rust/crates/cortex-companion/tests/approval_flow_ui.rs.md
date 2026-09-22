# rust/crates/cortex-companion/tests/approval_flow_ui.rs

## Qué tiene adentro

Archivo de 540 líneas.
B6 — Panels Sessions+Actions con aprobación por clic integrada a la máquina de estados (G-B3 UI).  FakeBackend con contadores + `ActionLog` en temp dir: los clicks se resuelven con `hit_test`, el reducer abre el modal (`pending`), y `effects::apply(ResolveApproval)` ejecuta SOLO lo aprobado, auditando en el action_log (cada ítem del lote por separado, spec 14 §5).
Tests: `click_approve_on_action_executes_and_audits`, `click_deny_on_modal_never_executes`, `batch_auto_ok_only_batchable_items`, `batch_with_two_batchables_audits_each_item_separately`, `session_close_button_guards_and_audits`, `modal_focus_trap_only_accepts_its_buttons`, `guarded_menu_row_opens_modal_not_direct_effect`, `guarded_effect_runcommand_never_executes_opens_modal_instead`, `batch_button_disabled_when_no_batchable`, `batch_button_hover_paints_accent`

## Para qué sirve

B6 — Panels Sessions+Actions con aprobación por clic integrada a la máquina de estados (G-B3 UI).  FakeBackend con contadores + `ActionLog` en temp dir: los clicks se resuelven con `hit_test`, el reducer abre el modal (`pending`), y `effects::apply(ResolveApproval)` ejecuta SOLO lo aprobado, auditando en el action_log (cada ítem del lote por separado, spec 14 §5).

## Relaciones

### Recibe de

- `use cortex_companion::app::{`
- `use cortex_companion::approval::ActionLog`
- `use cortex_companion::effects`
- `use cortex_companion::engine::{`
- `use cortex_companion::screens::actions_screen::{actions_areas, render_actions}`
- `use cortex_companion::{Screen, UiRequest}`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/tests/approval_flow_ui.rs`. 540 líneas.
