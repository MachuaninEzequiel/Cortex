# rust/crates/cortex-cli/src/main.rs

## Qué tiene adentro

`CLI_VERSION = "0.1.0"`. `root_command()` clap solo para `--help` self-golden (no es el parser real). `main`: lee argv; aviso CORTEX_PY; flags versión; help; argv vacío → TUI Home; `dispatch_native`; else error rc 2.

`dispatch_native` match del primer token (tabla en 00-estructura.md).

## Para qué sirve

Punto de entrada del CLI nativo. Baja física: nunca reenvía a Python.

## Relaciones

### Recibe de

- `std::env::args`, stdout is_terminal.
- `cortex_tui::app` para Home.
- `commands::*` y `memory_cmds`.

### Envía a

- stdout/stderr y `process::exit`.

### Notas de implementación observadas en el código

`--help` usa `render_help()` de un árbol clap **reducido** (no lista todos los comandos wireados). Integraciones detectan el binario con `cortex-cli --version`.
