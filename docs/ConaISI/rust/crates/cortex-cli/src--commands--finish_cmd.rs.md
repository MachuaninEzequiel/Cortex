# rust/crates/cortex-cli/src/commands/finish_cmd.rs

## Qué tiene adentro

`finish` / `finish-session`: `--session-id`, `--intent` auto|abandon|handoff, `--reason`, `--interactive` (no cableado: stderr y se omite), `--project-root`. Reusa `NativeFinishBackend` + `finish_session_text`.

## Para qué sirve

Cerrar sesión con evidencia desde CLI (mismo handler que MCP).

## Relaciones

### Recibe de

- cortex-mcp finish handler/backend.

### Envía a

- stdout resultado; errores si el texto empieza con ❌.

### Notas de implementación observadas en el código

Una sola implementación de cierre para CLI y MCP.
