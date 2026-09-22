# rust/crates/cortex-enterprise/src/retrieval.rs

## Qué tiene adentro

Puerto de `cortex.enterprise.retrieval_service`: búsqueda multi-scope con fusión RRF (k=60, rank desde 1, inserción estable) y pesos por scope.  Paridad crítica replicada: - `scores[key] += weight * 1/(k+rank)` en orden episódico-then-semántico; - `ranked_keys = sorted(scores, reverse=True)` ESTABLE sobre el orden de primera inserción; - preferencia enterprise SOLO para el objeto unificado (`existing is None or (existing.scope != 'enterprise' and this is)`); - keys: `semantic:{path}` / `semantic:title:{title}` / `episodic:content:{primeros160-normalizados}` / `episodic:{id}`.
Archivo de 377 líneas.
Símbolos públicos observados:
- `pub use crate::models::RetrievalScope`
- `pub struct RetrievalSourceConfig`
- `pub struct UnifiedHit`
- `pub struct RetrievalResult`
- `pub struct EnterpriseRetrievalService<B: SearchBackend>`

## Para qué sirve

Puerto de `cortex.enterprise.retrieval_service`: búsqueda multi-scope con fusión RRF (k=60, rank desde 1, inserción estable) y pesos por scope.  Paridad crítica replicada: - `scores[key] += weight * 1/(k+rank)` en orden episódico-then-semántico; - `ranked_keys = sorted(scores, reverse=True)` ESTABLE sobre el orden de primera inserción; - preferencia enterprise SOLO para el objeto unificado (`existing is None or (existing.scope != 'enterprise' and this is)`); - keys: `semantic:{path}` / `semantic:title:{title}` / `episodic:content:{primeros160-normalizados}` / `episodic:{id}`.

## Relaciones

### Recibe de

- `use cortex_app::episodic::MemoryEntry`
- `use crate::error::EnterpriseError`
- `use crate::models::EnterpriseOrgConfig`
- `use crate::sources::{`
- Contexto de crate `cortex-enterprise`: cortex-app, cortex-setup, cortex-workspace

### Envía a

- Crate `cortex-enterprise` envía hacia: cortex-cli enterprise, cortex-doctor, cortex-actions knowledge.promote, cortex-brain-app org_memory

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-enterprise/src/retrieval.rs`.
