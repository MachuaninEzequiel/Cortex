# rust/crates/cortex-cli/tests/cli_setup_composed.rs

## Qué tiene adentro

`setup composed`: instala COMPOSED + tríada y bloque Agent skills. Fixture tempdir.

## Para qué sirve

Obra 08 G-A4b.

## Relaciones

### Recibe de

- skills_bundle + setup_cmd.

### Envía a

- cargo test.

### Notas de implementación observadas en el código

Patrón tempfile como cli_commands_basic.
