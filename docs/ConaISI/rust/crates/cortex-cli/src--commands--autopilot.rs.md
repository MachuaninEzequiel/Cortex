# rust/crates/cortex-cli/src/commands/autopilot.rs

## Qué tiene adentro

Subcomandos nativos sobre `AutopilotService`: start (mode observe|assist|autopilot), preflight, checkpoint, finish, status, doctor. `install`/`uninstall` **eliminados** (usar `session hooks`); caen en `Other` → rc 2.

## Para qué sirve

Capa de decisión autopilot desde CLI.

## Relaciones

### Recibe de

- `cortex_autopilot::{config, policies, service}`.
- SessionStorage + WorkspaceLayout.
- `session_hooks::default_installer` en doctor.

### Envía a

- Session activa / JSON.

### Notas de implementación observadas en el código

VALID_MODES: observe, assist, autopilot.
