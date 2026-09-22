# rust/crates/cortex-actions/src/models.rs

## Qué tiene adentro

Puerto de `cortex/action_engine/models.py` (Obra 05 Fase B, §3.2 del plan).  Contrato duro replicado: 1. Toda acción delega en su servicio — nunca reimplementa lógica. 2. Las precondiciones se evalúan ANTES de ofrecer la acción. 3. `reversible=false` ⇒ requiere aprobación SIEMPRE (sin modo auto). 4. Toda ejecución se registra en `.cortex/action_log.jsonl`. 5. Dry-run nativo: `run(true)` devuelve el efecto sin escribir.
Archivo de 449 líneas.
Símbolos públicos observados:
- `pub enum Categoria`
- `pub enum Costo`
- `pub enum Trigger`
- `pub fn impacto_base(categoria: &str) -> f64`
- `pub fn costo_penalizacion(costo: &str) -> f64`
- `pub fn ahora_iso() -> String`
- `pub struct ActionResult`
- `pub struct Check`
- `pub struct Action`
- `pub struct ProposedAction`
- `pub struct Decision`
- `pub fn redondear(x: f64, decimales: usize) -> f64`
Tests en el mismo archivo: `auto_ok_exige_reversible_e_instant`, `reversible_exige_undo`, `id_formato_dominio_accion`, `check_roto_nunca_revienta`, `deep_only_se_omite_en_snapshot`, `dry_y_fail_mensajes`, `redondeo_compatible_python`

## Para qué sirve

Puerto de `cortex/action_engine/models.py` (Obra 05 Fase B, §3.2 del plan).  Contrato duro replicado: 1. Toda acción delega en su servicio — nunca reimplementa lógica. 2. Las precondiciones se evalúan ANTES de ofrecer la acción. 3. `reversible=false` ⇒ requiere aprobación SIEMPRE (sin modo auto). 4. Toda ejecución se registra en `.cortex/action_log.jsonl`. 5. Dry-run nativo: `run(true)` devuelve el efecto sin escribir.

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-actions`: cortex-app, cortex-enterprise, cortex-setup

### Envía a

- Crate `cortex-actions` envía hacia: cortex-cli next, cortex-companion, cortex-tui, .cortex/action_log.jsonl

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-actions/src/models.rs`.
