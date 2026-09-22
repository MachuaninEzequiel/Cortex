# rust/crates/cortex-setup/src/session_hooks/opencode.rs

## Qué tiene adentro

`OpencodeHookAdapter`. Bloque marcado en `.opencode/hooks.md`.

## Para qué sirve

Hooks OpenCode → checkpoint.

## Relaciones

### Recibe de

- target_dir proyecto.

### Envía a

- `.opencode/hooks.md`.

### Notas de implementación observadas en el código

Marcadores HTML `<!-- <<< cortex-session-hook <<< -->`.
