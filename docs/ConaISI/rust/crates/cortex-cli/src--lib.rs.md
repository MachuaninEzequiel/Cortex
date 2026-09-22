# rust/crates/cortex-cli/src/lib.rs

## Qué tiene adentro

`pub mod commands, memory, memory_cmds, paths, pyjson, rich_panel`.

## Para qué sirve

Exponer el CLI como librería para tests, examples y `cortex-companion` (que depende de cortex-cli).

## Relaciones

### Recibe de

- Módulos src/.

### Envía a

- `main.rs`, tests, companion.

### Notas de implementación observadas en el código

El binario solo despacha; la lógica vive en la lib.
