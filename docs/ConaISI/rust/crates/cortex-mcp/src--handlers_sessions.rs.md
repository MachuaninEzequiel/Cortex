# rust/crates/cortex-mcp/src/handlers_sessions.rs

## Qué tiene adentro

Mirrors `SCheckpoint`, `SHook`, `STask`, `SRecord`. Constantes de sources y task statuses. Trait `SessionsBackend`. Handlers texto:

- session_open/checkpoint/close/status/list
- session_task_list/update
- review_checkpoint
- close_session
- save_session
- validate_handoff (YAML AgentHandoff)
- verify_session_claims (git diff)

`to_string_ensure_ascii_false`.

## Para qué sirve

Familia sesiones del MCP (porte de `cortex/mcp/tools/sessions.py`).

## Relaciones

### Recibe de

- Args JSON del tool.
- `SessionsBackend` (prod: `NativeSessionsBackend`).
- `cortex_workspace` handoff en validate.
- git/project_root en verify_claims.

### Envía a

- JSON string al dispatcher.
- Disco vía backend (SessionService).

### Notas de implementación observadas en el código

Wire-format = `json.dumps(..., ensure_ascii=False)` con orden de inserción.
