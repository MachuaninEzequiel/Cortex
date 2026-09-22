# rust/crates/cortex-companion/tests/approval.rs

## Qué tiene adentro

Archivo de 193 líneas.
B2 — Flujo de aprobación: las mutaciones del Companion solo se ejecutan con aprobación explícita, y esa decisión (aprobado/denegado/fallo) queda auditada en el action_log con el MISMO formato de cortex-actions.
Tests: `denied_mutation_never_executes`, `approved_mutation_executes_and_audits`, `failure_is_audited_not_silent`, `audit_reuses_native_action_log_format`, `close_session_ya_no_manda_a_comando_muerto`

## Para qué sirve

B2 — Flujo de aprobación: las mutaciones del Companion solo se ejecutan con aprobación explícita, y esa decisión (aprobado/denegado/fallo) queda auditada en el action_log con el MISMO formato de cortex-actions.

## Relaciones

### Recibe de

- `use cortex_companion::approval::{run_guarded, ActionLog, ApprovalRequest, ApprovalUi}`
- `use cortex_companion::engine::Backend`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/tests/approval.rs`. 193 líneas.
