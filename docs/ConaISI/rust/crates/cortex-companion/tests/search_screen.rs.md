# rust/crates/cortex-companion/tests/search_screen.rs

## Qué tiene adentro

Archivo de 485 líneas.
B7 — Panel Search + feedback (G-B2d).  Cubre: `/` navega a Search; input teclado (Typed/Backspace); Enter con query no vacía dispara `Effect::Search` y vacío NO llama al backend; click [Útil] en fila episódica dispara `Effect::MarkUseful`; `effects::apply` persiste feedback en `.cortex/feedback.jsonl` con el MISMO formato del escritor del oráculo (`cortex/feedback_loop.py::add_feedback` + `FeedbackStore.append`: claves en orden type, memory_id, feedback_type, source, y ts completado al final; separadores `, `/`: `; feedback_type "positive" como la TUI) y es idempotente por hit; filas semánticas no tienen botón (sin memory_id, como core.py:274). Backend de test: registra queries de búsqueda y escribe feedback real en
Tests: `slash_navigates_to_search_from_other_screens`, `slash_in_search_is_query_text_not_navigation`, `backspace_edits_query`, `empty_query_does_not_search`, `search_runs_hybrid_and_marks_useful`, `semantic_rows_have_no_useful_button`, `search_error_is_visible_never_silent`, `feedback_dedupe_recognizes_both_positive_aliases`, `feedback_rotates_at_max_bytes_preserving_generation`, `feedback_line_serialization_matches_python_dumps`, `search_screen_renders_input_hits_and_budget`, `search_screen_prompts_empty_input`

## Para qué sirve

B7 — Panel Search + feedback (G-B2d).  Cubre: `/` navega a Search; input teclado (Typed/Backspace); Enter con query no vacía dispara `Effect::Search` y vacío NO llama al backend; click [Útil] en fila episódica dispara `Effect::MarkUseful`; `effects::apply` persiste feedback en `.cortex/feedback.jsonl` con el MISMO formato del escritor del oráculo (`cortex/feedback_loop.py::add_feedback` + `FeedbackStore.append`: claves en orden type, memory_id, feedback_type, source, y ts completado al final; separadores `, `/`: `; feedback_type "positive" como la TUI) y es idempotente por hit; filas semánticas no tienen botón (sin memory_id, como core.py:274). Backend de test: registra queries de búsqueda y escribe feedback real en

## Relaciones

### Recibe de

- `use cortex_companion::app::{`
- `use cortex_companion::approval::ActionLog`
- `use cortex_companion::effects`
- `use cortex_companion::engine::{Backend, DoctorSummary, SearchHit, SessionSummary, StatsSummary}`
- `use cortex_companion::feedback::{self, AppendOutcome}`
- `use cortex_companion::screens::search_screen::{render_search, search_areas, SearchData}`
- `use cortex_companion::{Screen, UiRequest}`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/tests/search_screen.rs`. 485 líneas.
