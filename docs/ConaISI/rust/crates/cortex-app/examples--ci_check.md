# examples/ci_check.rs

## Qué tiene adentro

`ci_check <fixtures_dir> <golden_dir>`. Reproduce `ci_golden_p11.py`: 10 escenarios validate-pr en tres formatos + flujo L3 review-sessions. Normaliza `{{ROOT}}`, `{{MS}}`, `{{DUR}}`, `{{DATE}}`.

## Para qué sirve

Paridad P11-ci.

## Relaciones

### Recibe de

- session+documenter+verification nativos.

### Envía a

- Comparación byte-a-byte vs golden.

### Notas de implementación observadas en el código

649 líneas; el checker más largo junto con p12a7.
