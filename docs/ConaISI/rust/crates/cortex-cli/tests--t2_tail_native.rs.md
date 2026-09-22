# rust/crates/cortex-cli/tests/t2_tail_native.rs

## Qué tiene adentro

Cola nativa del Cierre T2 (familias memoria/sesiones/acciones in-process).

## Para qué sirve

Asegurar dispatch nativo de la cola T2.

## Relaciones

### Recibe de

- memory_cmds / session / next.

### Envía a

- cargo test.

### Notas de implementación observadas en el código

Nombre T2 en el archivo.
