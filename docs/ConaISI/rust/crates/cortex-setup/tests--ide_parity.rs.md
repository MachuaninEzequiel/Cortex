# rust/crates/cortex-setup/tests/ide_parity.rs

## Qué tiene adentro

P8d: 11 adapters × escenarios fresh/existing/uninstall. HOME redirigido, now congelado. Normaliza `{{ROOT}}/{{HOME}}`. Reports ordenados (glob opencode no determinista).

## Para qué sirve

Paridad de archivos inyectados.

## Relaciones

### Recibe de

- adapters reales + goldens ide/.

### Envía a

- cargo test.

### Notas de implementación observadas en el código

Compara project + home trees.
