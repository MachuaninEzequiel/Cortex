# rust/crates/cortex-mcp/examples/cierre_check.rs

## Qué tiene adentro

Ejemplo/checker de cierre de tools no-sesión (familias search/docs/spec/finish) contra goldens.

## Para qué sirve

Gate de Cierre Obra 07 T1 fuera de la suite unitaria.

## Relaciones

### Recibe de

- Handlers + backends (stubs o nativos según el example).

### Envía a

- stdout PASS/FAIL.

### Notas de implementación observadas en el código

Se corre con `cargo run -p cortex-mcp --example cierre_check`.
