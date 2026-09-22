# src/documenter/diff_parser.rs

## Qué tiene adentro

`DiffAction`: Added/Deleted/Modified/Renamed/Copied. Códigos A/D/R/C; cualquier otro → Modified.

`DiffEntry { action, path (post-cambio), old_path }`.

`parse_name_status`: líneas `<status>\t<path>` o `<status>\t<old>\t<new>`. Vacías ignoradas. n≠2,3 → eprint y skip.

## Para qué sirve

Parsear `git diff --name-status` para el reconstructor.

## Relaciones

### Recibe de

- stdout de `git::diff_name_status`.

### Envía a

- `documenter::reconstruct_git` / `DiffEntrySer`.

### Notas de implementación observadas en el código

Unknown status cae a Modified, no error.
