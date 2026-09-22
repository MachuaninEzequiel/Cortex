# rust/crates/cortex-cli/tests/t_lea2_b_hu.rs

## Qué tiene adentro

`hu import` con Jira file:// en tmp, error provider desconocido, `--no-remember`.

## Para qué sirve

MITAD B ruta 2 HU.

## Relaciones

### Recibe de

- hu_cmd + WorkItemService.

### Envía a

- cargo test.

### Notas de implementación observadas en el código

Antes providers vacíos ⇒ siempre "Unknown work item provider: jira".
