# rust/crates/cortex-cli/examples/cli_check.rs

## Qué tiene adentro

Replay nativo de `golden_cli.txt`. Invoca binario `cortex-cli` con fixtures, normaliza `{{ROOT}}/{{TS}}/{{FP}}` como el oráculo Python. Uso: build golden + `cargo run -p cortex-cli --example cli_check -- <golden_dir>`.

## Para qué sirve

Paridad funcional live (no self-golden de --help).

## Relaciones

### Recibe de

- `bench/parity/archive/.p12b-cli/golden_cli.txt`.
- Binario debug cortex-cli.

### Envía a

- PASS/FAIL por segmento `### nombre`.

### Notas de implementación observadas en el código

`--help` y errores clap viven en `tests/cli_self_golden.rs`, no aquí.
