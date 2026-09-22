# Cargo.toml

## Qué tiene adentro

Paquete `cortex-embed`. Descripción: wrapper ONNX con dim paramétrica.

Dependencias opcionales:
- `ort = "2.0.0-rc.13"`
- `tokenizers = "0.23"`

Feature `onnx = ["dep:ort", "dep:tokenizers"]`. Dev-dep: `serde_json` (example spike).

## Para qué sirve

Aislar el runtime ONNX del dominio puro. Sin feature, el crate solo expone `EmbeddingDim`.

## Relaciones

### Recibe de

- Workspace (versión/edition/license).
- crates.io: ort, tokenizers.

### Envía a

- `cortex-app` lo declara con `features = ["onnx"]`.
- `cortex-py` feature `onnx` reexporta `cortex-embed/onnx`.

### Notas de implementación observadas en el código

`ort` descarga binarios de onnxruntime en su `build.rs`. Comentario: spike original quedó como example.
