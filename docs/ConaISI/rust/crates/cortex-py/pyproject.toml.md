# pyproject.toml

## Qué tiene adentro

Build-system maturin `>=1.0,<2.0`. Proyecto Python `cortex-core-native` 0.1.0, requires-python `>=3.11`.

`[tool.maturin]`: `python-source = "."`, `module-name = "cortex_core._native"`, `features = ["extension-module"]`.

Comentario de uso: `maturin develop --release -m rust/crates/cortex-py/Cargo.toml` desde la raíz (el `-m` evita el pyproject setuptools del repo).

## Para qué sirve

Empaquetar el binding sin interferir el `setuptools` de `cortex-memory`.

## Relaciones

### Recibe de

- `Cargo.toml` de este crate (maturin lo lee).

### Envía a

- Instala el paquete `cortex_core` (fuente `cortex_core/__init__.py` + extensión `_native`).

### Notas de implementación observadas en el código

El wheel nativo lleva el embedder ONNX porque `extension-module` activa `onnx`.
