# rust/crates/cortex-mcp/src/backends/sessions.rs

## Qué tiene adentro

`NativeSessionsBackend { SessionService }`. Storage en `root/.cortex/sessions`. Mapeo SessionRecord → SRecord. Helpers `srecord`, `frontmatter`.

## Para qué sirve

Implementar `SessionsBackend` 1:1 sobre SessionService nativo.

## Relaciones

### Recibe de

- `cortex_app::session::{SessionService, SessionStorage, CheckpointSource, TaskStatus}`.

### Envía a

- Handlers de sesiones.

### Notas de implementación observadas en el código

Source inválido cae a `CheckpointSource::Manual`.
