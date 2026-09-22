# Guardrails y CI

## A. Guardrails del Brain / Companion

Cubierto en `10-brain-mcp-tools.md` capa 3. Cookbook `llm_guardrails`.

Resumen operativo: un request TypeSafe por mensaje in (y opcionalmente out) con Noul jailbreak / asks_to_mutate + Score harm. Thresholds en el mismo archivo de questions. Brain no muta aunque el guardrail falle: fail-closed a “no dispatch + mostrar que hay que usar CLI”.

No poner guardrails TypeSafe en el MCP stdio de agentes IDE de entrada: el agente (Claude, etc.) ya tiene su propia policy; duplicar latencia en cada una de las 32 tools es caro y el state es el argumento JSON, no un chat. Si algún día se hace, solo en tools que **escriben** (`cortex_write_doc`, `cortex_finish_session`, `cortex_session_close`), no en search.

## B. Pipeline CI y `validate-pr`

Módulos: `cortex/pipeline/*` (security, lint, test, documentation stages), `cortex/ci/{validator,review_session,session_matcher,diff_io,markdown_formatter}.py`, `cortex-pipeline`, `cortex-app/src/ci/`.

Stages: deterministas. `abort_early`. GitHubActionsRunner emite YAML. DocumentationStage = gate de docs del PR.

`review_session.py`: abre una Session `CI_REVIEW`, checkpoints `CI_BOT`, cierra. No juzga semántica del diff: reporta.

`session_matcher`: ¿este PR matchea una sesión? Eso puede ser ids/paths (código) o semántica (¿el título del PR es esta spec?). Lo segundo sí es Choice/Noul:

```text
Noul pr_matches_session
  compare: [pr.title+body, session.spec_title+goal]
```

Si bajo y hay sesión open → comentario Markdown `warn` (el formatter ya existe), no fail del pipeline en v1. CI fail-closed por un noul sería demasiado: jaggedness + 429 en GitHub Actions.

Security stage del pipeline: linters/secrets scanners, no Jev. Un Noul “does this diff look like it introduces auth bypass” es tentador y **malo** como gate rojo: adversarial, literal, no es un SAST. Si se experimenta, solo comment `warn`, nunca `StageStatus` fail.

## C. Semantic code linting (use-case map TypeSafe)

TypeSafe lista “semantic lints de convenciones de equipo en CI”. En Cortex eso podría ser:

- ¿este PR toca el vault y no actualiza la spec de la sesión?
- ¿el handoff afirma files que el diff no toca?

Eso **ya** es quality gates + documenter. No hace falta un lint genérico “el código es limpio”. Reusar `08-session-quality-gates.md` en el comentario de PR (`markdown_formatter`), modo `warn`.

## D. Doctor y tutor

Zero tokens, offline. **Prohibido** llamar TypeSafe. Doctor checks: layout, gitignore, config, governance. Tutor: topics embebidos + `get_hint(ProjectState)`. Se quedan.

## E. Feedback loop

`feedback_loop.py` / `feedback_store.py` / Companion `feedback.jsonl`. Labels humanos (approve/deny de actions, review-knowledge). Son el dataset para calibrar umbrales y, más adelante, un CatBoost sobre probabilities (AutoResearch cookbook). No es un call TypeSafe: es el log que hace a TypeSafe mejorable.
