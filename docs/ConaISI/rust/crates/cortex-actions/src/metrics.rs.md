# rust/crates/cortex-actions/src/metrics.rs

## Qué tiene adentro

Puerto de `cortex/action_engine/metrics.py` (Obra 05 Fase E, plan §3.6).  - `pct_motor` = ejecuciones decididas por el motor (auto-ok, via=auto) sobre el total de ejecuciones reales (no dry-run). - Target declarado por el dueño: abrir el menú de acciones <1 vez por día de trabajo activo ⇒ proxy medible hoy: pct_motor alto con volumen estable de ejecuciones y dias_con_interaccion bajo.
Archivo de 183 líneas.
Símbolos públicos observados:
- `pub struct MetricasMotor`
- `pub fn calcular_metricas(log: &ActionLog) -> MetricasMotor`
Tests en el mismo archivo: `calculo_pct_motor`, `vacio`, `por_accion_orden_estable_por_conteo`

## Para qué sirve

Puerto de `cortex/action_engine/metrics.py` (Obra 05 Fase E, plan §3.6).  - `pct_motor` = ejecuciones decididas por el motor (auto-ok, via=auto) sobre el total de ejecuciones reales (no dry-run). - Target declarado por el dueño: abrir el menú de acciones <1 vez por día de trabajo activo ⇒ proxy medible hoy: pct_motor alto con volumen estable de ejecuciones y dias_con_interaccion bajo.

## Relaciones

### Recibe de

- `use crate::store::ActionLog`
- `use crate::store::OrderedEntry`
- Contexto de crate `cortex-actions`: cortex-app, cortex-enterprise, cortex-setup

### Envía a

- Crate `cortex-actions` envía hacia: cortex-cli next, cortex-companion, cortex-tui, .cortex/action_log.jsonl

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-actions/src/metrics.rs`.
