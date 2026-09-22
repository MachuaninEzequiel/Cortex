# examples/p12a1_check.rs

## Qué tiene adentro

`p12a1_check <fixtures_dir> <golden_dir> <model_dir>`. Secciones: `NativeEpisodicStore.append` según `append_specs.json`; compara golden_entries_after (`{{TS}}`), golden_rankings (orden vector), golden_after.jsonl (meta byte, embeddings tol ≤1e-4). También index_file / security paths.

## Para qué sirve

Paridad P12A-1 (escrituras nativas).

## Relaciones

### Recibe de

- Store JSONL, embedder real, security/semantic.

### Envía a

- Reporte vs goldens.

### Notas de implementación observadas en el código

Líneas previas del JSONL deben quedar byte-idénticas tras append.
