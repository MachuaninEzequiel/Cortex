# rust/crates/cortex-cli/src/paths.rs

## Qué tiene adentro

`python_resolve` (canonicaliza el ancestro existente más profundo + componentes restantes; lección: `file_name()` es None si el tramo es `..`). `expand_user` (`~` y `~/…` vía HOME). `resolve_project_root(Option<&str>)`.

## Para qué sirve

Igualar `Path.expanduser().resolve()` del CLI Python.

## Relaciones

### Recibe de

- cwd, HOME, `--project-root`.

### Envía a

- Todos los comandos que descubren el repo.

### Notas de implementación observadas en el código

Mismo algoritmo que cortex-doctor::native y cortex-enterprise::review_knowledge.
