# src/git.rs

## Qué tiene adentro

Puerto de `cortex/session/git.py`. Timeout 10s por polling (`try_wait` + sleep 20ms).

`GitError(String)`. `run(args, repo_root)` spawnea `git` con stdout/stderr piped. NotFound → `"git executable not found on PATH"`. Timeout mata el proceso.

Público: `is_git_repo` (`rev-parse --is-inside-work-tree` == `true`), `get_head_commit` (SHA 40-hex lowercase), `get_current_branch`, `diff(start,end)`, `diff_name_status`, `init_and_commit_all` (init `-b main`, user fixture, `commit.gpgsign=false`, fechas fijas `2026-08-24T12:00:00+00:00`).

## Para qué sirve

Subprocess git determinista para sesiones, documenter git-aware y fixtures.

## Relaciones

### Recibe de

- `repo_root` y refs del caller (`session`, `documenter`, `pr`, examples).

### Envía a

- stdout de git como `String`, o `GitError`.

### Notas de implementación observadas en el código

SHA de HEAD se valida longitud 40 y hex lowercase. `init_and_commit_all` usa `-c GIT_AUTHOR_DATE=...` (variables vía `-c`, no env).
