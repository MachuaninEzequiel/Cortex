# src/onnx.rs

## Qué tiene adentro

`OnnxEmbedder` (thread-unsafe; el binding lo envuelve en Mutex).

Constantes: `MAX_SEQ = 256` (chroma MiniLM), `CHUNK = 32` (batch interno).

`open(model_dir)` / `open_with_threads(model_dir, intra_threads)`:
- Lee `model_dir/tokenizer.json` y `model_dir/model.onnx`.
- Truncation HF: Right, LongestFirst, max 256, stride 0.
- Sesión ORT Level3 (`ORT_ENABLE_ALL`). `intra_threads` opcional.

`embed_batch(&[String]) -> Vec<Vec<f64>>`: sublotes de 32. Textos vacíos son responsabilidad del caller.

Pipeline por chunk:
1. `encode_batch` con padding dinámico al max del lote (no pad fijo 256).
2. Tensores int64: `input_ids`, `attention_mask`, `token_type_ids`.
3. Inferencia; salida 3D `[batch, seq, dim]`; `dim` se guarda en la primera corrida.
4. Mean-pooling con máscara; denom clip `1e-9`; L2 con guard `1e-12`.

## Para qué sirve

Embeddings productivos all-MiniLM-L6-v2 sobre los mismos artefactos que cachea chromadb, con paridad de pooling.

## Relaciones

### Recibe de

- Directorio de modelo chroma (`tokenizer.json` + `model.onnx`).
- Lotes de texto de `cortex-app` (semantic, context, reindex, episodic append) y `cortex-py::NativeEmbedder`.

### Envía a

- Vectores `f64` L2-normalizados, dim del modelo.

### Notas de implementación observadas en el código

Padding dinámico: posiciones enmascaradas no aportan al mean-pool. El comentario afirma cos=1.0 vs OnnxEmbedder Python. No hay `unsafe` en este archivo.
