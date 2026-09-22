# rust/crates/cortex-workspace/Cargo.toml

## Qué tiene adentro

Manifiesto del crate `cortex-workspace` (versión/edición/licencia del workspace). Dependencias: `serde`, `serde_json`, `serde_yaml`. Dev-dependencies: `tempfile` y `sha2` (gate P12B-1: hashes del bundle de skills vs recursos Python).

## Para qué sirve

Declara el crate como librería pura de dominio de workspace, sin pyo3 ni otros crates Cortex.

## Relaciones

### Recibe de

- Workspace Cargo (`version.workspace`, etc.).

### Envía a

- Cargo/rustc al construir el crate.

### Notas de implementación observadas en el código

Sin features opcionales. El crate declara `#![forbid(unsafe_code)]` en `lib.rs`.
