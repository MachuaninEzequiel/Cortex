# src/ci/session_matcher.rs

## Qué tiene adentro

`find_session_for_pr(...)` — prioridad explicit > base_commit > head_branch > none. Delega en `SessionService::find_for_pr`.

## Para qué sirve

Encontrar la Session dueña de un PR.

## Relaciones

### Recibe de

- IDs/commits/branch del payload CI.

### Envía a

- `CiValidator`.

### Notas de implementación observadas en el código

Archivo corto (113 líneas): wrapper del servicio.
