# rust/crates/cortex-tui/src/search.rs

## Qué tiene adentro

Pantalla BUSCAR (spec §12 adaptada): input con cursor visible, búsqueda vía el motor inyectado (adapter del CLI sobre NativeMemory — la TUI no duplica retrieval), resultados con fuente/score/título/path, conteo y estados vacío/error explícitos.  Dos fases (spec: "Enter confirma; Esc limpia y restaura"): INPUT (escribir/editar) y LIST (navegar j/k, Enter muestra la ruta del hit).
Archivo de 452 líneas.
Símbolos públicos observados:
- `pub fn render(f: &mut Frame<'_>, state: &AppState)`
Tests en el mismo archivo: `input_muestra_query_y_cursor`, `submit_emite_efecto_de_busqueda`, `submit_vacio_no_busca`, `backspace_edita_y_esc_vuelve_a_input`, `lista_muestra_hits_fuente_escore`, `sin_resultados_es_explicito_y_reversible`, `enter_en_hit_notifica_la_ruta`

## Para qué sirve

Pantalla BUSCAR (spec §12 adaptada): input con cursor visible, búsqueda vía el motor inyectado (adapter del CLI sobre NativeMemory — la TUI no duplica retrieval), resultados con fuente/score/título/path, conteo y estados vacío/error explícitos.  Dos fases (spec: "Enter confirma; Esc limpia y restaura"): INPUT (escribir/editar) y LIST (navegar j/k, Enter muestra la ruta del hit).

## Relaciones

### Recibe de

- `use crate::app::search::SearchData`
- `use crate::app::state::{AppState, LoadState, Overlay, SearchMode}`
- `use crate::components::empty_state::EmptyState`
- `use crate::components::header::AppHeader`
- `use crate::components::list::SelectableList`
- `use crate::components::status_bar::StatusBar`
- `use crate::components::truncate_visual`
- `use crate::layout::{layout_mode, render_too_small, LayoutMode}`
- `use crate::theme::{StatusKind, Theme}`
- `use crate::app::search::SearchHit`
- `use crate::app::update as reducer`
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/search.rs`.
