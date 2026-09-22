# rust/crates/cortex-cli/tests/cli_finish.rs

## Qué tiene adentro

Tests del subcomando finish / finish-session.

## Para qué sirve

Cierre de sesión por CLI.

## Relaciones

### Recibe de

- finish_cmd + NativeFinishBackend.

### Envía a

- cargo test.

### Notas de implementación observadas en el código

Comparte handler MCP.
