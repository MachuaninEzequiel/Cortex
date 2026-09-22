# rust/crates/cortex-enterprise/src/sources.rs

## Qué tiene adentro

Puerto de `cortex.enterprise.sources`: lectores multi-vault y multi-episódico. Los tipos son owned y anotan origen (scope/project/ vault/persist_dir) exactamente como los `model_copy(update=…)` de Python.
Archivo de 110 líneas.
Símbolos públicos observados:
- `pub enum SourceScope`
- `pub struct VaultSource`
- `pub struct EpisodicSource`
- `pub struct SemanticHit`
- `pub struct EpisodicHit`
- `pub trait SearchBackend: Send`

## Para qué sirve

Puerto de `cortex.enterprise.sources`: lectores multi-vault y multi-episódico. Los tipos son owned y anotan origen (scope/project/ vault/persist_dir) exactamente como los `model_copy(update=…)` de Python.

## Relaciones

### Recibe de

- `use crate::error::EnterpriseError`
- `use cortex_app::episodic::MemoryEntry`
- Contexto de crate `cortex-enterprise`: cortex-app, cortex-setup, cortex-workspace

### Envía a

- Crate `cortex-enterprise` envía hacia: cortex-cli enterprise, cortex-doctor, cortex-actions knowledge.promote, cortex-brain-app org_memory

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-enterprise/src/sources.rs`.
