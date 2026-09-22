# examples/persister_check.rs

## Qué tiene adentro

`persister_check <golden_dir> <templates_dir>`. Compara kwargs de `create()` + render minijinja.

## Para qué sirve

Paridad P5c.

## Relaciones

### Recibe de

- Reconstruction goldens y templates.

### Envía a

- Render de nota.

### Notas de implementación observadas en el código

Templates no van embebidos en el example; se pasan por argv.
