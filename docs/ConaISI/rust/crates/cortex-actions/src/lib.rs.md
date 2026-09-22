# rust/crates/cortex-actions/src/lib.rs

## Qué tiene adentro

cortex-actions — puerto del ActionEngine (Obra 07 fase P6).  Puerto 1:1 de `cortex/action_engine/` (Obra 05): ciclo OBSERVAR → PROPONER → APROBAR → EJECUTAR → APRENDER.  Contrato duro replicado (models.py §docstring): 1. Toda acción delega en su servicio — nunca reimplementa lógica. 2. Las precondiciones se evalúan ANTES de ofrecer la acción. 3. `reversible=false` ⇒ requiere aprobación SIEMPRE (sin modo auto). 4. Toda ejecución se registra en `.cortex/action_log.jsonl`. 5. Dry-run nativo: `run(dry_run=true)` devuelve el efecto sin escribir.
Archivo de 27 líneas.
Símbolos públicos observados:
- `pub mod catalog`
- `pub mod context`
- `pub mod learning`
- `pub mod metrics`
- `pub mod models`
- `pub mod registry`
- `pub mod runner`
- `pub mod scheduler`
- `pub mod signals`
- `pub mod store`

## Para qué sirve

cortex-actions — puerto del ActionEngine (Obra 07 fase P6).  Puerto 1:1 de `cortex/action_engine/` (Obra 05): ciclo OBSERVAR → PROPONER → APROBAR → EJECUTAR → APRENDER.  Contrato duro replicado (models.py §docstring): 1. Toda acción delega en su servicio — nunca reimplementa lógica. 2. Las precondiciones se evalúan ANTES de ofrecer la acción. 3. `reversible=false` ⇒ requiere aprobación SIEMPRE (sin modo auto). 4. Toda ejecución se registra en `.cortex/action_log.jsonl`. 5. Dry-run nativo: `run(dry_run=true)` devuelve el efecto sin escribir.

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-actions`: cortex-app, cortex-enterprise, cortex-setup

### Envía a

- Crate `cortex-actions` envía hacia: cortex-cli next, cortex-companion, cortex-tui, .cortex/action_log.jsonl

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-actions/src/lib.rs`.
