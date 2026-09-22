# rust/crates/cortex-enterprise/src/review_knowledge.rs

## Qué tiene adentro

Puerto de `cortex.cli.review_knowledge`: operaciones de la cola de revisión y renderización comprobable. El registro clap llega en P12B-8 (CLI nativo último); acá sólo viven dominio + strings de salida exactos.
Archivo de 124 líneas.
Símbolos públicos observados:
- `pub struct PendingDraft`
- `pub(crate) fn python_resolve(path: &Path) -> std::path::PathBuf`
- `pub fn approve_output(`
- `pub fn reject_output(`
- `pub fn audit_timestamp(clock: &dyn Clock) -> String`

## Para qué sirve

Puerto de `cortex.cli.review_knowledge`: operaciones de la cola de revisión y renderización comprobable. El registro clap llega en P12B-8 (CLI nativo último); acá sólo viven dominio + strings de salida exactos.

## Relaciones

### Recibe de

- `use cortex_workspace::WorkspaceLayout`
- `use crate::clock::{isoformat_full, Clock}`
- `use crate::error::EnterpriseError`
- `use crate::promotion_doctype::{mark_as_accepted, mark_as_rejected}`
- Contexto de crate `cortex-enterprise`: cortex-app, cortex-setup, cortex-workspace

### Envía a

- Crate `cortex-enterprise` envía hacia: cortex-cli enterprise, cortex-doctor, cortex-actions knowledge.promote, cortex-brain-app org_memory

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-enterprise/src/review_knowledge.rs`.
