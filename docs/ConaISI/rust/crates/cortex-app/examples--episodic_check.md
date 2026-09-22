# examples/episodic_check.rs

## Qué tiene adentro

`episodic_check <golden_dir> <model_dir>`. Compara entries.json, vector_rankings.json, keyword.json, entity_order.json (conjuntos) usando `exported.jsonl`.

## Para qué sirve

Paridad P3.

## Relaciones

### Recibe de

- `NativeEpisodicStore` + goldens + embedder.

### Envía a

- exit 0/1 del checker.

### Notas de implementación observadas en el código

entity_order se compara por conjuntos, no orden interno de chroma.
