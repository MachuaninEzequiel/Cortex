# Cargo.toml

## Qué tiene adentro

Paquete `cortex-app`. Dependencias: `minijinja`, `unicode-normalization`, `chrono`, `uuid` (v4, default-features false), `regex`, `sha2`, `serde`/`serde_json`/`serde_yaml`, path crates `cortex-embed` (feature onnx), `cortex-setup`, `cortex-config`, `cortex-core`. Dev: `tempfile`.

## Para qué sirve

Declarar la capa de aplicación y enganchar embeddings ONNX + dominio + writers de setup + config.

## Relaciones

### Recibe de

- Workspace (minijinja, chrono, sha2, serde).
- `cortex-core` (store, scoring implícito vía search propio).
- `cortex-embed` OnnxEmbedder.
- `cortex-setup` (writers `build_note` usado por workitems).
- `cortex-config` (reindex).

### Envía a

- Todos los crates de aplicación/CLI/MCP listados en `00-estructura.md`.

### Notas de implementación observadas en el código

No hay binario en este crate; solo lib. Examples son bins de paridad.
