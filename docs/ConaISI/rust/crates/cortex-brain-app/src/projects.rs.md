# rust/crates/cortex-brain-app/src/projects.rs

## Qué tiene adentro

Scan de proyectos Cortex en `$HOME` (fallback `USERPROFILE`):

- Heurística: directorio con `.cortex/` + config (`.cortex/config.yaml` | `config.yaml` | `.cortex/workspace.yaml`)
- `ProjectEntry { path, branch, has_session, valid_config, last_scan }`
- `SKIP_DIRS` (node_modules, target, .venv, Library, .cache, …), `MAX_DEPTH=8`
- Cache `~/.cache/cortex/brain-projects.json` versión 1: mtime + sha256 de config; `list_projects` no recorre el árbol; `refresh_projects` sí
- `config.yaml` corrupto se lista con `valid_config: false` (no se oculta)
- Sesión activa: `.cortex/sessions/active.txt` no vacío + `<id>.yaml` existe (sin depender de `cortex-app`/ONNX)
- Branch: `.git/HEAD` `ref: refs/heads/<x>`
- Al detectar un proyecto, no baja a subdirectorios (evita fixtures)

## Para qué sirve

Sidebar de la app y flag `--projects-list` (`path\tbranch\tstatus`).

## Relaciones

### Recibe de

- filesystem HOME, git HEAD, sessions, yaml

### Envía a

- `list_projects` / `refresh_projects` Tauri y `main.rs`

### Notas de implementación observadas en el código

No usa `cortex-app` a propósito (evitar `ort-sys` en el build de la GUI).
