# rust/crates/cortex-cli/Cargo.toml

## Qué tiene adentro

Package `cortex-cli`, binario `src/main.rs`. clap sin default-features (std, help, usage, derive). Lista de crates Cortex de dominio + ratatui 0.30. Dev: tempfile.

## Para qué sirve

Definir el binario instalable (`cargo install --path rust/crates/cortex-cli`).

## Relaciones

### Recibe de

- Todos los crates listados en dependencies.

### Envía a

- El binario `cortex-cli` y la lib para tests/companion.

### Notas de implementación observadas en el código

`serde_json` con `float_roundtrip`. Descripción: “fachada de arranque instantáneo”.
