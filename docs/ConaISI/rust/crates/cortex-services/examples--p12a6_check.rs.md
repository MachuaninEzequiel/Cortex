# rust/crates/cortex-services/examples/p12a6_check.rs

## Qué tiene adentro

Checker P12A-6. Uso: `p12a6_check <golden_dir>`. Compara `migrate_vault`/`validate_vault` contra el oráculo de `cortex.documentation.migration`.

## Para qué sirve

Gate de paridad del migrador.

## Relaciones

### Recibe de

- Goldens y `cortex_services::migration`.

### Envía a

- Código de salida PASS/FAIL.

### Notas de implementación observadas en el código

Ejemplo cargo.
