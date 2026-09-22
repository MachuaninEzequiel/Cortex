# rust/crates/cortex-actions/src/catalog.rs

## Qué tiene adentro

Fábricas de acciones (1322 líneas). Cada una recibe `ActionContext` y arma `Action` con precondiciones, costo, dry-run y `run_fn`.

| id | efecto observado |
|---|---|
| `setup.finish_bootstrap` | Si no hay config: escribe workspace.yaml, config.yaml, org.yaml, vault architecture/context/decisions/runbooks, dirs memory/sessions vía `cortex_setup::setup_templates`. Dry-run lista faltantes (no toca disco). |
| `session.close_stale` | Report-only: OPEN >7 días sin checkpoints. Companion no cierra. |
| `session.checkpoint_now` | `git status --porcelain` + `SessionService::checkpoint` Manual. |
| `vault.reindex` | `cortex_app::reindex::reindex_vault` (modelo MiniLM ONNX). |
| `vault.validate_docs` | `DocValidator::validate_batch` hasta 200 md. |
| `quality.run_gates` | `review_checkpoint` último CP vs `files_in_scope` de spec. |
| `learn.topic` | Rotación diaria `TUTOR_TOPICS` (día del año local). |
| `knowledge.promote` | `KnowledgePromotionService` discover/review/plan/apply (`actor=companion`). |
| `memory.prune` | ≥3 feedbacks `not_useful`/`negative`; borra de jsonl episódico; `reversible=false`. |
| `ide.resync` | `all_adapters()` inject_profiles/mcp si hay configs presentes. |
| `session.suggest_next_phase` | Cadena grill→spec→plan→implement→review→close. |

`build_default_registry` registra en ese orden. `next_phase` mapea `CheckpointPhase`.

## Para qué sirve

Único catálogo v1 del motor de acciones. Scheduler/runner no reimplementan lógica de negocio.

## Relaciones

### Recibe de

- `ActionContext` (repo, vault, sesiones, config)
- `cortex_setup`, `cortex_app` (session, reindex, validator, quality_gates, episodic), `cortex_enterprise`

### Envía a

- `Registry` → scheduler → CLI `next` / Companion Actions / TUI

### Notas de implementación observadas en el código

Report-only usa `reversible=true` + undo no-op. Bootstrap dry-run documenta un bug histórico de Python (dry_run creaba archivos).
