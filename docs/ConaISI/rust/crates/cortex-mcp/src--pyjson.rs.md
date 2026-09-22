# rust/crates/cortex-mcp/src/pyjson.rs

## Qué tiene adentro

`py_float_repr(f64)`: replica `repr(f)` de CPython 3.12 (`.0` en enteros, `1e+20`, `-0.0`, nan/inf).

## Para qué sirve

Evitar que Rust imprima `0` donde Python imprime `0.0` en JSON de tools.

## Relaciones

### Recibe de

- Handlers que serializan floats.

### Envía a

- Strings numéricos en payloads MCP.

### Notas de implementación observadas en el código

Cortes científicos 1e-4 .. 1e16. Tests internos de floats.
