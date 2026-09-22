# rust/crates/cortex-companion/tests/current_branch.rs

## Qué tiene adentro

Archivo de 76 líneas.
current_branch (G-B2b, engine): lectura pura de fs con `.git` directorio (repo normal) y `.git` archivo (worktree) — sin subprocess.
Tests: `branch_from_git_dir_ref`, `branch_from_git_file_worktree`, `detached_head_yields_none`, `no_git_yields_none`

## Para qué sirve

current_branch (G-B2b, engine): lectura pura de fs con `.git` directorio (repo normal) y `.git` archivo (worktree) — sin subprocess.

## Relaciones

### Recibe de

- `use cortex_companion::engine::InProcessBackend`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/tests/current_branch.rs`. 76 líneas.
