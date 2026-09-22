# examples/g5_spike.rs

## Qué tiene adentro

Example CLI del spike G5. Sin feature `onnx` imprime error y sale.

Con feature: args `<model.onnx> <tokenizer.json> <texts.json>` (JSON array de strings). Tokeniza, carga sesión ORT Level3, infiere, mean-pool + L2, escribe vectores a `G5_OUT` o `/tmp/g5_rust.json`. Env `G5_DEBUG` imprime ids/máscaras/hidden.

## Para qué sirve

Comparar coseno contra una referencia Python (`bench/g5_reference.py` citado en el comentario del example) sin pasar por la API de librería.

## Relaciones

### Recibe de

- Archivos de modelo y `texts.json` por argv.
- `serde_json`, `ort`, `tokenizers`.

### Envía a

- stdout (timings, shape) y JSON de vectores pooleados.

### Notas de implementación observadas en el código

El padding usa `width = max_len` del batch. El pooling indexa `attention_mask[i * seq + t]` (seq = width del pad). No usa `OnnxEmbedder`; duplica el pipeline.
