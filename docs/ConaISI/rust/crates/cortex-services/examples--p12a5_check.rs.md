# rust/crates/cortex-services/examples/p12a5_check.rs

## Qué tiene adentro

Checker P12A-5. Uso: `p12a5_check <golden_dir>`. Compara SpecService + NoteService contra goldens.

## Para qué sirve

Gate de paridad de creación de spec/nota fuera de `cargo test`.

## Relaciones

### Recibe de

- Goldens en disco y API de `cortex-services`.

### Envía a

- Código de salida PASS/FAIL.

### Notas de implementación observadas en el código

Ejemplo cargo, no binario instalable.
