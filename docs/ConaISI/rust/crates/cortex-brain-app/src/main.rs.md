# rust/crates/cortex-brain-app/src/main.rs

## Qué tiene adentro

Entrypoint del binario `cortex-brain`:

- `Role::App`: si `try_connect` ok, manda `kind=focus` y sale (“ya está corriendo”); si no, `run()`
- `Role::ProjectsList`: lee cache o `refresh_projects`; imprime `path\tbranch\tstatus` (`invalid`/`session`/`ok`)
- `Role::QueryClient`: parsea `--query` y `--project`; conecta; envía request; imprime chunks en vivo; `done` es texto autoritativo; lista `> TOOL:`; exit 2 si no hay GUI o falta texto

## Para qué sirve

Tres roles en un binario: GUI, listado machine-readable, cliente IPC.

## Relaciones

### Recibe de

- argv, `ipc`, `projects`, `chat::ToolCall`

### Envía a

- stdout/stderr; socket del server GUI

### Notas de implementación observadas en el código

Si hay chunks, el texto de tools se imprime después desde `done` (los chunks son crudos del modelo).
