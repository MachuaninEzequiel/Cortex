# rust/crates/cortex-cli/tests/cli_self_golden.rs

## Qué tiene adentro

Congela textos `--help` y errores de args clap (Typer ≠ clap por diseño).

## Para qué sirve

Self-golden cosmética; paridad funcional está en cli_golden_p12b.py.

## Relaciones

### Recibe de

- stdout del binario.

### Envía a

- cargo test.

### Notas de implementación observadas en el código

Mismo precedente que ANSI del tutor P12B-7.
