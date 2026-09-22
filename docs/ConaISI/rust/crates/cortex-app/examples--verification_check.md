# examples/verification_check.rs

## Qué tiene adentro

`verification_check <golden_dir>`. VerificationRunner + quality_gates. Normaliza `duration_ms→{{D}}` y `run_at→{{TS}}`.

## Para qué sirve

Paridad P4-fin.

## Relaciones

### Recibe de

- Goldens + hooks.

### Envía a

- Comparación normalizada.

### Notas de implementación observadas en el código

Tiempos no son contrato.
