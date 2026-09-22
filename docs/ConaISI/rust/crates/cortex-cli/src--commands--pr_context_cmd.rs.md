# rust/crates/cortex-cli/src/commands/pr_context_cmd.rs

## Qué tiene adentro

Pipeline DevSecDocOps: `capture` (metadata PR → `.pr-context.json`), `store` (episódico + lint/audit/test results), `search` (PRs similares), `generate` (DocGenerator al vault), `full` (pasos 1–5 + sync).

## Para qué sirve

Ingesta de PRs en memoria y docs.

## Relaciones

### Recibe de

- `cortex_app::{pr, doc_generator, episodic::AppendParams}`.
- NativeMemory para search/sync.

### Envía a

- `.pr-context.json`, vault, episódico.

### Notas de implementación observadas en el código

Lo invoca el script `devsecdocops.sh` embebido en setup_templates_gen.
