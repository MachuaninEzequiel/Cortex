# tests/parity_fixtures.rs

## Qué tiene adentro

Un test: `dumps_identicos_al_oraculo_python_para_cada_fixture`.

Lee `bench/parity/fixtures_config/*.yaml` (ruta relativa `CARGO_MANIFEST_DIR/../../../bench/parity`). Para cada stem, llama `cortex_config::load_and_dump` y compara el string completo contra `bench/parity/archive/golden_config/{stem}.json`. Exige ≥8 fixtures.

## Para qué sirve

Gate de paridad P1: dump Rust ≡ dump Python.

## Relaciones

### Recibe de

- Fixtures YAML y goldens JSON del árbol `bench/parity`.
- `cortex_config::load_and_dump`.

### Envía a

- Resultado de `cargo test -p cortex-config`.

### Notas de implementación observadas en el código

Si falta un golden, panic con hint de `bench/parity/archive/capture_config_golden.py`. El test no invoca Python en runtime: compara contra goldens archivados.
