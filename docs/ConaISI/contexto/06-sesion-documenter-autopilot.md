# Contexto: sesión, documenter, autopilot (ciclo de trabajo)

## Session

Modelo: `SessionRecord` + `Checkpoint` (Python `cortex/session/models.py`, Rust `cortex-app/src/session/` y `cortex-autopilot/src/session_models.rs`).

Ciclo: open → checkpoint* → close. Ancla: una spec. Storage: YAML en `sessions_dir`.

`CheckpointSource` (SSoT, también enum MCP): `cortex-sync`, `cortex-SDDwork`, `cortex-code-explorer`, `cortex-code-implementer`, `cortex-code-designer`, `user-skill`, `ide-hook`, `manual`, `ci-bot`.

Tasks: `pending | in-progress | done | skipped | blocked`.

Quality gates: `session/quality_gates.rs` / `quality_gates.py`. Verification de claims: `verification.rs` / `verification.py` (el MCP `cortex_verify_session_claims` la expone).

`SpecService.create` abre sesión. CLI: `cortex session …`. MCP: `cortex_session_open/checkpoint/close/status/list` + task_list/task_update + `cortex_review_checkpoint`.

Hooks IDE: al editar (Claude Code) o al commit (Cursor) disparan `cortex session checkpoint --source ide-hook`.

## Documenter / finish

Al cerrar trabajo: reconstruir lo hecho desde diff + checkpoints, persistir notas, cerrar sesión.

Python: `cortex/documenter/` (diff_parser, reconstruction, contradiction_detector, adr_evaluator, interactive, persistence, spec_loader). CLI `finish`/`finish-session` en `cli/documenting.py`. Config `documenter.default_mode`: `auto | interactive`.

Rust: `cortex-app/src/documenter/` (diff_parser, handoff, interactive, persister, spec_loader) + `doc_generator` / `doc_validator` / `doc_verifier`. CLI nativo `finish`/`finish-session`. MCP: `cortex_finish_session`, `cortex_documenter_briefing`, `cortex_close_session`, `cortex_self_review_note`, `cortex_write_doc`.

`confidence` de `MemoryEntry` nace acá: verified / asserted / contradicted según el Verification Gate contra el diff.

## Autopilot

Capa de decisión encima de la sesión.

Detectores (`cortex-autopilot/src/detectors/`): CodeChange, DocsOnly, QuestionOnly, SecuritySensitive, LargeRefactor, Noop, AmbiguousRequest.

Policies: modos + enforcement + budget profiles (`DEFAULT_BUDGET_PROFILE = "fast_code"`).

Lifecycle: start → preflight → checkpoint → finish, más status. Service: `AutopilotService` con trait `DocumenterFinalize`. Errores tipados `AutopilotError`.

CLI: `cortex autopilot …`. MCP: cinco tools `cortex_autopilot_*`. Python: `cortex/autopilot/service.py` + cli.

## Pipeline (CI)

`PipelineOrchestrator` corre stages en orden: security, lint, test, documentation. Cada uno `StageResult` con `StageStatus`. `abort_early` en config. `GitHubActionsRunner` emite YAML. `DocumentationStage` es el gate de docs del PR (junto a `cortex-app/src/ci/` validate-pr: diff_io, session_matcher, review_session, markdown_formatter).

## Next / acciones sugeridas

`cortex next` consulta el ActionEngine: contexto (sesión, vault, git, signals de 14 días) → catálogo → scheduler top 5 → propuestas con comando exacto. Companion las muestra en `actions_screen` con approve/deny. Brain solo las propone.
