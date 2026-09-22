# rust/examples/dbg_ap.rs

## Qué tiene adentro

`main` crea un `tempdir`, llama `cortex_workspace::WorkspaceLayout::discover(&root)` e imprime `repo_root` y `workspace_root`.

## Para qué sirve

Smoke manual de discovery de layout, no es un binario de producto.

## Relaciones

### Recibe de
`cortex-workspace::WorkspaceLayout`.

### Envía a
stdout.
