# rust/crates/cortex-tui/src/session_detail.rs

## Qué tiene adentro

Pantalla DETALLE DE SESIÓN (spec §11.4 adaptada al dominio real): la sesión seleccionada con identidad, checkpoints, verificación y tareas — datos reales del `SessionRecord` nativo. Read-only (el diff preview del oráculo rich espera `compute_diff` nativo, aún no portado — anotado).  Scroll vertical con `j/k`; el reducer no conoce el máximo de líneas: el render clampea el offset al rango real (determinista, sin estado extra).
Archivo de 635 líneas.
Símbolos públicos observados:
- `pub struct CheckpointRow`
- `pub struct VerificationRow`
- `pub struct TaskRow`
- `pub struct SessionDetailData`
- `pub fn render(f: &mut Frame<'_>, state: &AppState)`
Tests en el mismo archivo: `build_lines_cubre_secciones`, `diff_error_se_muestra_sin_romper_el_detalle`, `diff_largo_se_trunca_con_footer`, `duracion_formateada`

## Para qué sirve

Pantalla DETALLE DE SESIÓN (spec §11.4 adaptada al dominio real): la sesión seleccionada con identidad, checkpoints, verificación y tareas — datos reales del `SessionRecord` nativo. Read-only (el diff preview del oráculo rich espera `compute_diff` nativo, aún no portado — anotado).  Scroll vertical con `j/k`; el reducer no conoce el máximo de líneas: el render clampea el offset al rango real (determinista, sin estado extra).

## Relaciones

### Recibe de

- `use crate::app::state::{AppState, LoadState}`
- `use crate::components::empty_state::EmptyState`
- `use crate::components::header::AppHeader`
- `use crate::components::status_bar::StatusBar`
- `use crate::components::truncate_visual`
- `use crate::keymap::global_hints`
- `use crate::layout::{layout_mode, render_too_small, LayoutMode}`
- `use crate::sessions::rel_time`
- `use crate::theme::{StatusKind, Theme}`
- `use cortex_app::session::{SessionRecord, TaskStatus}`
- `use crate::theme::Theme`
- `use cortex_branding::ansi::ColorMode`
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/session_detail.rs`.
