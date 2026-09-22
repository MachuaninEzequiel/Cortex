# rust/crates/cortex-tui/tests/sessions_screen.rs

## Qué tiene adentro

Archivo de 216 líneas.
Gate CIERRE T6 — pantalla sesiones ratatui.  Contrato: (a) los DATOS mostrados son idénticos a lo que emite `cortex session list --json` (`_record_summary` + orden newest-first + marca de activa), verificado contra la serialización JSON de las mismas filas; (b) snapshot render bajo presupuesto <50ms; (c) determinismo y estado vacío. Fuente canónica: SessionService nativo sobre fixtures reales en tmp. Dos sesiones reales con timestamps fijados por YAML directo (determinista).
Tests: `datos_mostrados_iguales_a_session_list_json`, `filtro_por_status_y_activo_nulo`, `pantalla_vacia_mensaje_contratual`, `render_determinista`, `render_bajo_presupuesto_50ms`

## Para qué sirve

Gate CIERRE T6 — pantalla sesiones ratatui.  Contrato: (a) los DATOS mostrados son idénticos a lo que emite `cortex session list --json` (`_record_summary` + orden newest-first + marca de activa), verificado contra la serialización JSON de las mismas filas; (b) snapshot render bajo presupuesto <50ms; (c) determinismo y estado vacío. Fuente canónica: SessionService nativo sobre fixtures reales en tmp. Dos sesiones reales con timestamps fijados por YAML directo (determinista).

## Relaciones

### Recibe de

- `use cortex_app::session::service::SessionService`
- `use cortex_app::session::{CheckpointSource, SessionStorage}`
- `use cortex_tui::app::{update as reducer, Action, AppState}`
- `use cortex_tui::sessions::{SessionRow, SessionsScreenData, RENDER_BUDGET_MS}`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/tests/sessions_screen.rs`. 216 líneas.
