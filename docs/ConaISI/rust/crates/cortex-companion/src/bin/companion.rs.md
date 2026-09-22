# rust/crates/cortex-companion/src/bin/companion.rs

## Qué tiene adentro

Binario `cortex-companion`. Flags: `--project-root`, `--mode {normal,sidecar,float,copilot}`, `--model <gguf>` / `--no-model`, `-h`. Default root = cwd. Llama `runner::run_app`. `#![forbid(unsafe_code)]`.

## Para qué sirve

Entrada TUI mouse-first en modo Normal (u otros vía `--mode`). Los bins sidecar/float/copilot fuerzan el modo sin parsear `--mode`.

## Relaciones

### Recibe de

- argv, cwd

### Envía a

- `cortex_companion::runner::run_app(mode, root, model)`

### Notas de implementación observadas en el código

`--model` sin valor o valor que empieza con `--` es error exit 2.
