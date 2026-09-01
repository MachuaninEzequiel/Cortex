//! cortex-actions — puerto del ActionEngine (Obra 07 fase P6).
//!
//! Puerto 1:1 de `cortex/action_engine/` (Obra 05): ciclo
//! OBSERVAR → PROPONER → APROBAR → EJECUTAR → APRENDER.
//!
//! Contrato duro replicado (models.py §docstring):
//! 1. Toda acción delega en su servicio — nunca reimplementa lógica.
//! 2. Las precondiciones se evalúan ANTES de ofrecer la acción.
//! 3. `reversible=false` ⇒ requiere aprobación SIEMPRE (sin modo auto).
//! 4. Toda ejecución se registra en `.cortex/action_log.jsonl`.
//! 5. Dry-run nativo: `run(dry_run=true)` devuelve el efecto sin escribir.
//!
//! Paridad-como-contrato: los tests Python de `tests/unit/action_engine/`
//! son LA especificación; el gate de fase compara `next --stats` y el
//! catálogo propuesto (`next --json`) contra el CLI Python sobre fixtures
//! deterministas (`bench/parity/actions_golden_p6.py`).

pub mod catalog;
pub mod context;
pub mod learning;
pub mod metrics;
pub mod models;
pub mod registry;
pub mod runner;
pub mod scheduler;
pub mod signals;
pub mod store;
