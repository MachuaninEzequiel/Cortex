# rust/crates/cortex-cli/tests/t_lea_b_docs.rs

## Qué tiene adentro

`docs` validate/restore/list-backups y routing-table nativos.

## Para qué sirve

MITAD B docs.

## Relaciones

### Recibe de

- docs_cmd + migration.

### Envía a

- cargo test.

### Notas de implementación observadas en el código

Antes no dispatchados ⇒ passthrough rc 127.
