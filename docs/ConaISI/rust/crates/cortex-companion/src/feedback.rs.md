# rust/crates/cortex-companion/src/feedback.rs

## Qué tiene adentro

Escritor de feedback explícito para el Companion (B7, G-B2d).  Porteo del formato canónico del oráculo: `cortex/feedback_loop.py::FeedbackCollector.add_feedback` (claves en orden `type`, `memory_id`, `feedback_type`, `source`; `ts` lo completa `FeedbackStore.append` al final vía `setdefault` — `json.dumps` default con separadores `", "` / `": "`) + `cortex/feedback_store.py` (append JSONL, rotación a `feedback.1.jsonl` al superar `max_bytes`, una sola generación histórica).  El escaper es `cortex_cli::pyjson::write_escaped` (ensure_ascii=True de CPython). El oráculo escribe con ensure_ascii=False, pero todos los
Archivo de 178 líneas.
Símbolos públicos observados:
- `pub const FEEDBACK_FILE: &str = "feedback.jsonl"`
- `pub const FEEDBACK_ROTATED: &str = "feedback.1.jsonl"`
- `pub const MAX_BYTES_DEFAULT: u64 = 5 * 1024 * 1024`
- `pub enum AppendOutcome`
- `pub fn dumps_event(`
- `pub fn append_useful(`
Tests en el mismo archivo: `iso_ts_has_offset_and_millis`

## Para qué sirve

Escritor de feedback explícito para el Companion (B7, G-B2d).  Porteo del formato canónico del oráculo: `cortex/feedback_loop.py::FeedbackCollector.add_feedback` (claves en orden `type`, `memory_id`, `feedback_type`, `source`; `ts` lo completa `FeedbackStore.append` al final vía `setdefault` — `json.dumps` default con separadores `", "` / `": "`) + `cortex/feedback_store.py` (append JSONL, rotación a `feedback.1.jsonl` al superar `max_bytes`, una sola generación histórica).  El escaper es `cortex_cli::pyjson::write_escaped` (ensure_ascii=True de CPython). El oráculo escribe con ensure_ascii=False, pero todos los

## Relaciones

### Recibe de

- `use cortex_cli::pyjson::write_escaped`
- Contexto de crate `cortex-companion`: cortex-cli, cortex-actions, cortex-app, cortex-config, cortex-workspace, cortex-branding, cortex-brain, herdr CLI

### Envía a

- Crate `cortex-companion` envía hacia: TUI ratatui, action_log.jsonl, panes herdr

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/src/feedback.rs`.
