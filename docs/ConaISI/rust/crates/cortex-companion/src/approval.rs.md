# rust/crates/cortex-companion/src/approval.rs

## Qué tiene adentro

- `ApprovalRequest { title, effect, audit_key }`
- Trait `ApprovalUi::ask` → true = [Ejecutar]
- `ActionLog` wrapper de `cortex_actions::store::ActionLog` (mismo `action_log.jsonl`, mismas claves ordenadas)
- `run_guarded`: si deniega, audita `outcome=denied` y `Ok`; si aprueba, corre `f`; éxito `executed`, fallo `failed` y propaga error. Append usa `.expect` (nunca gobernado sin registro)

## Para qué sirve

Ninguna mutación del Companion se ejecuta directa: modal + auditoría.

## Relaciones

### Recibe de

- UI (`app::pending`, screens actions/sessions)
- `cortex_actions::store::{ActionLog as NativeLog, OrderedEntry}`

### Envía a

- `.cortex/action_log.jsonl`
- Result al `effects` / estado

### Notas de implementación observadas en el código

Denegar no es error de sistema. Mismo archivo que el runner nativo.
