# Cargo.toml

## Qué tiene adentro

Paquete `cortex-py`. `[lib] name = "_native"`, `crate-type = ["cdylib", "rlib"]`.

Features:
- `extension-module = ["pyo3/extension-module", "onnx"]` — lo activa maturin; no es default para que `cargo test` linkee libpython.
- `onnx = ["cortex-embed/onnx"]`.

Deps: `pyo3 0.29` con `abi3-py311`, `numpy 0.29`, path a `cortex-core` y `cortex-embed`.

## Para qué sirve

Definir el extension module ABI3 para Python ≥3.11.

## Relaciones

### Recibe de

- `cortex-core`, `cortex-embed`, PyO3, numpy.

### Envía a

- Wheel/`maturin develop` instala `cortex_core._native` en el venv.

### Notas de implementación observadas en el código

ABI3 py311: un binario para 3.11+.
