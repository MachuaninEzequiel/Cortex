# rust/crates/cortex-cli/tests/cli_commands_basic.rs

## Qué tiene adentro

Tests de agent-guidelines, install-skills y doctor (bytes exactos donde el oráculo es determinista; doctor estructura/rc).

## Para qué sirve

Smoke de comandos triviales P12B-8 Task 2.

## Relaciones

### Recibe de

- Binario + tempfile.

### Envía a

- cargo test.

### Notas de implementación observadas en el código

Paridad completa en gate Python con STUB_TABLE.
