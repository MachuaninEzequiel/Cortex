# cortex/runtime_context.py

## Qué tiene adentro

- `slugify(value, fallback="default")` — minúsculas, no alfanum → `-`.
- `_run_git_command` — `git` cwd=project, timeout 5s, stdout o None.
- `detect_git_branch` → rama o `"no-git-branch"`.
- `detect_git_repo_path` → toplevel git o el path dado.
- `resolve_episodic_persist_dir(project_root, episodic_cfg)`:
  - `namespace_mode=project` (default): `project_root / persist_dir`.
  - `branch`: `.../branches/<slug-rama>`.
  - `custom`: `.../custom/<namespace_value slugged>`.

## Para qué sirve

Helpers de identidad de runtime (proyecto/rama) y de dónde vive Chroma.

## Relaciones

### Recibe de

- `git` subprocess, dict `episodic` del YAML.

### Envía a

- `core.AgentMemory` (project_id, branch, persist dir, metadata).
- `doctor`, `webgraph.service`, `enterprise.models.slugify` (enterprise importa `slugify` de aquí).

---
Fuente: lectura completa de `cortex/runtime_context.py`. No se usó documentación previa.
