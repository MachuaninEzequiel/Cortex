# rust/crates/cortex-workspace/src/runtime_context.rs

## Qué tiene adentro

- `slugify(value, fallback)`: minúsculas, no `[a-zA-Z0-9._-]` → un `-`, trim de `-`, vacío → fallback.
- `run_git_command` interno: `git` con timeout 5s, stderr nulo; error/timeout/rc≠0/stdout vacío → `None`.
- `detect_git_branch` → rama o `"no-git-branch"`.
- `detect_git_repo_path` → toplevel o el propio project_root.
- `EpisodicNamespaceCfg { persist_dir, namespace_mode, namespace_value }`.
- `resolve_episodic_persist_dir`: `branch` → `<base>/branches/<slug>`, `custom` → `<base>/custom/<slug>`, resto → `<base>`.

## Para qué sirve

Namespacing de memoria episódica y detección git usada al abrir stores.

## Relaciones

### Recibe de

- Binario `git` en PATH.
- Config episódica (`persist_dir`, `namespace_mode`, `namespace_value`).
- `layout::resolve_lexical`.

### Envía a

- `cortex-cli::memory::EpisodicLoad` (resuelve el JSONL).
- Cualquier consumidor que persista memoria por rama/proyecto.

### Notas de implementación observadas en el código

El timeout se implementa con `try_wait` + sleep 10ms (no `wait_timeout` crate). Fallback de branch para slug: `"detached"`.
