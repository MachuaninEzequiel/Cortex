# examples/bm25_search.rs

## Qué tiene adentro

Runner CLI: `bm25_search <vault> <queries.jsonl> <top_k> <limit>`. Construye `SemanticIndex::build` y emite JSON `{"queries":[{"query", "paths":[rel...]}]}` en orden de ranking.

## Para qué sirve

Gate de paridad P2a vs `VaultReader._bm25_search`.

## Relaciones

### Recibe de

- Vault y queries jsonl.

### Envía a

- stdout JSON comparado por harness de paridad.

### Notas de implementación observadas en el código

Solo paths, no scores.
