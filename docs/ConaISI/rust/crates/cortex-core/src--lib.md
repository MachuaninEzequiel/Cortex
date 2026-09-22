# src/lib.rs

## Qué tiene adentro

Módulo raíz. Constante `pub const VERSION: &str = env!("CARGO_PKG_VERSION")`. Declara `pub mod bm25; scoring; store; webgraph`. Test `smoke_version` exige `VERSION == "0.1.0"` y no vacío.

El comentario de crate fija la regla: no depende de `pyo3`; la fachada Python vive en `cortex-py` (`cortex_core._native`). Invariantes: `dim` de vectores siempre paramétrica; paridad antes que velocidad.

## Para qué sirve

Punto de entrada del dominio nativo y etiqueta de versión que el binding reporta con `core_version()`.

## Relaciones

### Recibe de

- Cargo (versión del paquete).
- Submódulos del mismo crate.

### Envía a

- `cortex-py::core_version` lee `cortex_core::VERSION`.
- Consumidores nativos importan `cortex_core::{scoring, store, bm25, webgraph}`.

### Notas de implementación observadas en el código

Los cuatro módulos se portean «un gate por vez» (G1 scoring, G2 store, G3 BM25, G4 webgraph). El test de versión está acoplado al `0.1.0` del workspace.
