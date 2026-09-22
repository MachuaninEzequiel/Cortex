# rust/crates/cortex-setup/src/session_hooks/mod.rs

## Qué tiene adentro

`InstallResult`, `UninstallResult`, `HookStatus`. Trait `HookAdapter`. `HookInstaller` registry (list/get/install/uninstall/status/status_all). `default_installer`: claude_code, cursor, opencode, pi. Helpers `strip_block`, `read_or_empty`, `write_lf`.

## Para qué sirve

Instalar artefactos IDE que al dispararse corren `cortex session checkpoint --source ide-hook`.

## Relaciones

### Recibe de

- CLI `session hooks` y `ide status`.

### Envía a

- Adapters de hooks.

### Notas de implementación observadas en el código

Segundo install detecta existente y no falla. JSON inválido → Err(String).
