# examples/semantic_search.rs

## Qué tiene adentro

`semantic_search <vault> <model_dir> <queries.jsonl> <top_k> <limit>`. Índice + embeddings ONNX + ranking vectorial.

## Para qué sirve

Paridad P2b.

## Relaciones

### Recibe de

- Vault, modelo ONNX, queries.

### Envía a

- stdout ranking.

### Notas de implementación observadas en el código

Requiere artefactos MiniLM.
