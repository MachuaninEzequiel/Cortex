# rust/crates/cortex-setup/tests/writers_parity.rs

## Qué tiene adentro

Paridad P8b: writers vs goldens `bench/parity/archive/golden_setup/writers`. Reloj fijo 2026-08-24.

## Para qué sirve

Byte-a-byte de notas canónicas.

## Relaciones

### Recibe de

- `build_note` + goldens.

### Envía a

- cargo test.

### Notas de implementación observadas en el código

Goldens archivados en baja física.
