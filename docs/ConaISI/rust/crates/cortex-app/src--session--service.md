# src/session/service.rs

## Qué tiene adentro

Capa de servicio sobre `SessionStorage` (P11-ci). `SessionService { storage, repo_root }` es `Clone`.

`SessionMatchKind`: explicit / by_commit / by_branch / none.

API observada:
- `compute_diff(session_id)`: gitless → `""`; si no `git diff start_commit..end_commit|HEAD`.
- `save_new_record` falla si existe (`SessionAlreadyExists`).
- `write_session_lock`: best-effort `.cortex/session.lock` con `{id}\n`; fallo FS no rompe el ciclo.
- `get`, `get_active` (puntero stale → None), `set_active` (solo OPEN), `list`.
- `find_for_pr(explicit, base_commit, head_branch)`: prioridad explícito > commit > branch > none.
- `now_iso()` RFC3339 micros offset `+00:00` (`SecondsFormat::Micros, false`).

También open/checkpoint/close con sufijos `-2`, `-3` para ids únicos (documentado en el módulo; el archivo continúa ~500 líneas).

## Para qué sirve

API que consume `cortex.ci` y la CLI de sesión, con lock para lectores externos.

## Relaciones

### Recibe de

- `SessionStorage`, `git` (indirecto), records YAML.

### Envía a

- `ci::validator`, `ci::review_session`, `ci::session_matcher`, TUI (test `compute_diff` menciona clone para thread), CLI.

### Notas de implementación observadas en el código

No hay lock por-archivo en mutate (un hilo). `compute_diff` no usa `crate::git::diff` (timeout 10s); llama `Command::new("git")` directo.
