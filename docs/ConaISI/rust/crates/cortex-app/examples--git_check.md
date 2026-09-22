# examples/git_check.rs

## Qué tiene adentro

`git_check <workspace> <session_id>`. Reconstrucción git-aware. Emite JSON con SHAs→`{{SHA}}` y ws→`{{ROOT}}`.

## Para qué sirve

Paridad P5b.

## Relaciones

### Recibe de

- Repo real + session id.

### Envía a

- JSON normalizado.

### Notas de implementación observadas en el código

Usa `crate::git` timeout 10s.
