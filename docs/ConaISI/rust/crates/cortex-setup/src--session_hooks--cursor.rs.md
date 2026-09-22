# rust/crates/cortex-setup/src/session_hooks/cursor.rs

## Qué tiene adentro

`CursorGitHookAdapter`. A pesar del nombre: bloque en `.git/hooks/post-commit` (cualquier IDE que haga git commit). SHA+subject; `|| true` para no fallar el commit. exec bit. Uninstall solo el bloque marcado.

## Para qué sirve

Checkpoint post-commit.

## Relaciones

### Recibe de

- Repo git.

### Envía a

- `.git/hooks/post-commit`.

### Notas de implementación observadas en el código

Si el usuario ya tenía hook, se agrega bloque separado.
