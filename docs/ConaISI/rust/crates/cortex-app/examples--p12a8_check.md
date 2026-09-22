# examples/p12a8_check.rs

## Qué tiene adentro

`p12a8_check <golden_dir>`. Máquina de estados `documenter::interactive`.

## Para qué sirve

Paridad P12A-8.

## Relaciones

### Recibe de

- `InteractiveSession` con input inyectado.

### Envía a

- Goldens de transcript/resultados.

### Notas de implementación observadas en el código

Rich no se compara; sí el resultado de `prompt()`.
