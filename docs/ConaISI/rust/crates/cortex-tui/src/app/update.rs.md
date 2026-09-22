# rust/crates/cortex-tui/src/app/update.rs

## Qué tiene adentro

Reducer puro (spec §2/§16.1): `update(&mut AppState, Action) -> Effect`. Sin IO, sin render, sin terminal — testeable sin TTY. El runtime ejecuta el efecto y devuelve acciones de datos.
Archivo de 1083 líneas.
Símbolos públicos observados:
- `pub fn update(state: &mut AppState, action: Action) -> Effect`
- `pub fn keep_selection_visible(state: &mut AppState)`
- `pub fn copy_selection(state: &AppState) -> Option<String>`
Tests en el mismo archivo: `quit_pide_efecto`, `esc_cierra_overlay_primero`, `movimiento_respeta_limites`, `pagina_se_mueve_por_viewport`, `offset_mantiene_seleccion_visible`, `resize_ajusta_viewport_y_seleccion`, `sesiones_cargadas_resetean_seleccion_si_vacia`, `error_no_revienta_y_reintenta_con_tick`, `notificaciones_experian`, `errores_no_experian`, `acciones_reversibles_se_ejecutan_con_un_enter`, `acciones_irreversibles_requieren_doble_enter`, `esc_cancela_la_confirmacion`, `action_finished_notifica_y_libera`, `q_no_es_bloqueado_por_confirmacion_en_reducer`

## Para qué sirve

Reducer puro (spec §2/§16.1): `update(&mut AppState, Action) -> Effect`. Sin IO, sin render, sin terminal — testeable sin TTY. El runtime ejecuta el efecto y devuelve acciones de datos.

## Relaciones

### Recibe de

- `use crate::layout::layout_mode`
- `use crate::theme::StatusKind`
- `use crate::sessions::{SessionRow, SessionsScreenData}`
- `use crate::actions::{ActionView, ActionsData}`
- `use crate::actions::{ActionView, ActionsData}`
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/app/update.rs`.
