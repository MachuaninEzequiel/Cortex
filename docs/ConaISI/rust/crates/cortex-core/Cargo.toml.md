# Cargo.toml

## Qué tiene adentro

Manifiesto del paquete `cortex-core`. Hereda `version`, `edition` y `license` del workspace. Descripción: «Dominio puro de Cortex en Rust: scoring, store vectorial, BM25, webgraph.» Única dependencia: `rayon = "1"`.

## Para qué sirve

Declara el crate de dominio sin bindings. `rayon` se usa en `bm25.rs` (scores por documento) y `webgraph.rs` (pares i<j y escaneo cross-source).

## Relaciones

### Recibe de

- Workspace raíz `rust/Cargo.toml` (versión, edition, license).

### Envía a

- Cargo resuelve este crate para `cortex-py`, `cortex-app` y `cortex-webgraph-server`.

### Notas de implementación observadas en el código

No hay features. No hay `pyo3`. El comentario de `lib.rs` prohíbe bindings en este crate.
