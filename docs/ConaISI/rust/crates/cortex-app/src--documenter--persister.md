# src/documenter/persister.rs

## Qué tiene adentro

Puerto de `_write_session_note` hasta `create()` + self-review.

Constantes: `PLACEHOLDER_TOKENS` (7), `SUCCESS_CLAIM_PATTERNS` (9), `SELF_REVIEW_TAG = "auto-draft"`.

`CreateArgs`, `TaskOut`. `summarize_tasks`, `self_review_draft(reconstruction, draft_body) -> Vec<String>`, `build_create_args`.

Render de la nota usa minijinja (example `persister_check` pasa `templates_dir`).

## Para qué sirve

Convertir `ReconstructionOutput` en kwargs del writer canónico de nota de sesión.

## Relaciones

### Recibe de

- `ReconstructionOutput`, `session::Task`.
- Templates Jinja (`cortex-setup` / dir Python de templates).

### Envía a

- Writer `build_note` / filesystem vault sessions.

### Notas de implementación observadas en el código

Self-review etiqueta `auto-draft`. Placeholders distintos de quality_gates (7 vs 3).
