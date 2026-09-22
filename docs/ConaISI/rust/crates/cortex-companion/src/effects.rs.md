# rust/crates/cortex-companion/src/effects.rs

## Qué tiene adentro

B6 — Aplicación de efectos compartida entre el binario y los tests.  El reducer (`app::update`) es puro: declara `Effect`. Este módulo es el runtime que los aplica contra el `Backend` inyectado, y es el ÚNICO lugar donde una mutación puede ejecutarse: siempre a través de `run_guarded` (B2) con la decisión que el usuario tomó en el modal de la máquina de estados. Así el flujo auditado es idéntico en producción y en tests (nada de loops bloqueantes ni lógica duplicada en el binario).  B8 añade el brain híbrido: `apply_opt` acepta el `LlmBackend` opcional (None = router determinista, cero tokens; Some = protocolo TOOL del brain con las tools enrutadas por el engine in-process — `brain_panel`).
Archivo de 268 líneas.
Símbolos públicos observados:
- `pub struct AnsweredUi`
- `pub fn apply<B: Backend>(be: &B, log: &ActionLog, st: &mut AppState, fx: Effect)`
- `pub fn apply_opt<B: Backend>(`

## Para qué sirve

B6 — Aplicación de efectos compartida entre el binario y los tests.  El reducer (`app::update`) es puro: declara `Effect`. Este módulo es el runtime que los aplica contra el `Backend` inyectado, y es el ÚNICO lugar donde una mutación puede ejecutarse: siempre a través de `run_guarded` (B2) con la decisión que el usuario tomó en el modal de la máquina de estados. Así el flujo auditado es idéntico en producción y en tests (nada de loops bloqueantes ni lógica duplicada en el binario).  B8 añade el brain híbrido: `apply_opt` acepta el `LlmBackend` opcional (None = router determinista, cero tokens; Some = protocolo TOOL del brain con las tools enrutadas por el engine in-process — `brain_panel`).

## Relaciones

### Recibe de

- `use crate::app::{AppState, ApprovalTarget, Effect, OutcomeLine, PendingApproval}`
- `use crate::approval::{run_guarded, ActionLog, ApprovalRequest, ApprovalUi}`
- `use crate::brain_panel::{self, BrainMsg}`
- `use crate::engine::Backend`
- `use crate::feedback`
- `use crate::menu::{self, MenuOutput}`
- Contexto de crate `cortex-companion`: cortex-cli, cortex-actions, cortex-app, cortex-config, cortex-workspace, cortex-branding, cortex-brain, herdr CLI

### Envía a

- Crate `cortex-companion` envía hacia: TUI ratatui, action_log.jsonl, panes herdr

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/src/effects.rs`.
