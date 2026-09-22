# src/session/mod.rs

## Qué tiene adentro

Primitiva de sesión (P4). Constantes: `GITLESS_COMMIT_PLACEHOLDER` (40 ceros), `MAX_VERIFICATION_OUTPUT_BYTES = 10_000`.

Enums serde:
- `SessionStatus`: open/closed/handoff/abandoned; `is_terminal` = closed|handoff|abandoned.
- `SessionMode`: unknown, managed, observed, byo, composed, `ci-review`.
- `CheckpointPhase`: grill, spec, plan, implement, review, close (`parse` case-sensitive minúsculas).
- `CheckpointSource`: cortex-sync, cortex-SDDwork, cortex-code-explorer/implementer/designer, user-skill, ide-hook, manual, ci-bot.
- `TaskStatus`: pending, in-progress, done, skipped, blocked.

Modelos `deny_unknown_fields`: `Task` (id `T\d+(\.\d+)*`), `Checkpoint` (phase opcional skip_serializing_if None), `VerificationHook` (required default true, success_criteria `"exit code 0"`, timeout 300), `VerificationHookResult`, `SessionRecord`.

`SessionRecord::validate`: session_id `YYYY-MM-DD_<slug>`, SHA 40-hex lowercase, ISO-8601 con offset, tasks, invariantes OPEN vs terminal (closed_at/end_commit/documenter_decision). `is_gitless` si start_commit es placeholder.

`infer_mode`: vacío→BYO; todos ci-bot→CI_REVIEW; cualquier phase→COMPOSED; todos sources Cortex→MANAGED; resto OBSERVED.

`truncate_output`: conserva últimos 10_000 bytes con prefijo de aviso.

`SessionStorage`: dir `.cortex/sessions`; `{id}.yaml` tmp+rename; `active.txt`; `list_all` yaml sorted. `canonical_json_normalized` sustituye timestamps por `{{TS}}` y root por `{{ROOT}}`.

Submódulos: `quality_gates`, `service`, `verification`.

## Para qué sirve

Persistir el ciclo de vida de una sesión de trabajo (open/checkpoint/close) con paridad YAML/JSON vs Python.

## Relaciones

### Recibe de

- Callers CLI/MCP/CI; git SHAs; checkpoints de skills/hooks.

### Envía a

- `session::service`, `documenter`, `ci`, examples `session_check`.

### Notas de implementación observadas en el código

Datetimes son strings, no tipos chrono en el modelo. `serde_yaml::to_string` no fuerza `sort_keys`; el comentario afirma orden de declaración.
