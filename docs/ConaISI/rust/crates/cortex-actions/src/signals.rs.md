# rust/crates/cortex-actions/src/signals.rs

## Qué tiene adentro

Puerto de `cortex/action_engine/signals.py` (Obra 05 Fase E).  La marca [y]=útil de la búsqueda TUI (y cualquier feedback explícito persistido) alimenta la prioridad: dominio negativo ⇒ suben calidad/ mantenimiento (retrieval malo = problemas de índice/docs); dominio positivo ⇒ suben aprendizaje/conocimiento. Ventana por defecto: 14 días.
Archivo de 273 líneas.
Símbolos públicos observados:
- `pub const VENTANA_DIAS_DEFAULT: i64 = 14`
- `pub struct MemorySignals`
- `pub fn leer_senales(dot_cortex: &Path, dias: i64) -> MemorySignals`
- `pub fn multiplicador_categoria(categoria: &str, senales: Option<&MemorySignals>) -> f64`
Tests en el mismo archivo: `lee_ventana_y_descarta_fuera_de_ella`, `dominio_negativo_y_positivo`, `multiplicadores_por_dominio`, `tope_25_porciento`, `neutro_es_neutro`, `scheduler_con_senales_espejo_fase_e`

## Para qué sirve

Puerto de `cortex/action_engine/signals.py` (Obra 05 Fase E).  La marca [y]=útil de la búsqueda TUI (y cualquier feedback explícito persistido) alimenta la prioridad: dominio negativo ⇒ suben calidad/ mantenimiento (retrieval malo = problemas de índice/docs); dominio positivo ⇒ suben aprendizaje/conocimiento. Ventana por defecto: 14 días.

## Relaciones

### Recibe de

- `use crate::models::ActionResult`
- `use crate::models::{Action, Categoria, Costo}`
- `use crate::registry::Registry`
- `use crate::scheduler::Scheduler`
- `use crate::store::PreferencesStore`
- Contexto de crate `cortex-actions`: cortex-app, cortex-enterprise, cortex-setup

### Envía a

- Crate `cortex-actions` envía hacia: cortex-cli next, cortex-companion, cortex-tui, .cortex/action_log.jsonl

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-actions/src/signals.rs`.
