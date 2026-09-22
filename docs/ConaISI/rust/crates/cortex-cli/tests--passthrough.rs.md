# rust/crates/cortex-cli/tests/passthrough.rs

## Qué tiene adentro

Fija que `CORTEX_BIN` no tiene efecto y no se ejecuta binario externo. Arranque nativo instantáneo. Baja física: sin reenvío a Python.

## Para qué sirve

Contrato residual post-eliminación de passthrough.

## Relaciones

### Recibe de

- Binario cortex-cli / env.

### Envía a

- cargo test.

### Notas de implementación observadas en el código

`CORTEX_PY` tampoco delega.
