# examples/p12a3_check.rs

## Qué tiene adentro

`p12a3_check <golden_dir>`. S01–S12 de captura PR. cwd tmp SIN git (git → vacío). `hu_references` se emite ordenado.

## Para qué sirve

Paridad P12A-3.

## Relaciones

### Recibe de

- `pr.rs`.

### Envía a

- `golden_p12a3.txt`.

### Notas de implementación observadas en el código

Orden de hu_references no es contrato en Python (set); el checker ordena.
