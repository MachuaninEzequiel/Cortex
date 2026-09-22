# rust/crates/cortex-cli/src/commands/review.rs

## Qué tiene adentro

Subcomandos: `pending` (drafts, filtro doc-type, --json), `approve`, `reject` (--delete), `candidate` (legacy JSONL KnowledgePromotionService). Actor/reviewer default usuario OS (LOGNAME/USER/...).

## Para qué sirve

`cortex review-knowledge`.

## Relaciones

### Recibe de

- `cortex_enterprise::review_knowledge` / promotion.
- vault-enterprise.

### Envía a

- Notas con audit_trail; stdout tabla/JSON.

### Notas de implementación observadas en el código

Reject por default mueve a `rejected/`.
