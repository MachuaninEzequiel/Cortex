# rust/crates/cortex-cli/src/commands/session_cmd.rs

## Qué tiene adentro

Familia `cortex session`:

- `current`, `checkpoint`, `switch`, `diff`, `abandon`, `list`, `show`
- `watch` | `tui` (ratatui snapshot si no TTY)
- `task` (list/update)
- `hooks` list|install|uninstall|status (HookInstaller)

JSON de records = pydantic `model_dump(mode="json")`. Tabla rich de `list` byte-parity.

## Para qué sirve

Operar SessionRecord nativo (P4) desde CLI.

## Relaciones

### Recibe de

- `SessionService` + `SessionStorage` en `layout.sessions_dir()`.
- `cortex_setup::session_hooks` para hooks.
- `cortex_tui` para watch.

### Envía a

- `.cortex/sessions/` JSONL/archivos de sesión.
- stdout tablas/JSON.

### Notas de implementación observadas en el código

Sources: mismos 9 CheckpointSource. Sin subcomando → rc 2.
