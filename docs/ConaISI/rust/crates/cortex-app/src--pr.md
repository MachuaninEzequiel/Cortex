# src/pr.rs

## Qué tiene adentro

Puerto de `pr_capture` + `PRContext` + `PRService` (P12A-3).

`PRContext` campos en orden pydantic: pr_number, title, body, author, source/target_branch (default target `main`), commit_sha, files_changed, diff_summary, db_migrations, api_changes, labels, lint/audit/test_result Option.

Métodos: `hu_references()` — 4 regex IGNORECASE, dedup por conjunto (orden no contrato).

Captura: `get_files_changed` / `_in`, `get_diff_summary` / `_in` (git), `detect_db_migrations`, `detect_api_changes`, `capture_from_env`, `capture_from_github` (`PR_NUMBER` no numérico → 0, más tolerante que Python ValueError), `CaptureManualArgs` + `capture_manual`/`_in`, `capture_from_json`, `save_context` (JSON indent 2, nulls explícitos, UTF-8 crudo).

`enrich_with_pipeline`. `PRService` usa `DocGenerator` y traits `SemanticIndexer`/`EpisodicSink` de workitems. `generate_pr_docs`/`write_pr_docs` se cablean en P12A-4.

## Para qué sirve

Capturar contexto de un PR y persistirlo / generar docs fallback.

## Relaciones

### Recibe de

- git, env GitHub, JSON, `doc_generator`, workitems traits.

### Envía a

- Archivo JSON de contexto; vault via generator; CLI `cortex pr-context`; example `p12a3_check`.

### Notas de implementación observadas en el código

JSON es contrato byte-parity con `model_dump_json(indent=2)`.
