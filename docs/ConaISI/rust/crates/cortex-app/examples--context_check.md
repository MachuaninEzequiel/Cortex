# examples/context_check.rs

## Qué tiene adentro

`context_check <fixtures_dir> <golden_dir> <model_dir>`. Reproduce `context_golden_p7.py`: carga JSONL, indexa vault, tres casos, compara bundles (floats 6 decimales, matched_by ordenado, `{{ROOT}}`).

## Para qué sirve

Paridad P7 del enricher.

## Relaciones

### Recibe de

- `ContextEnricher` + nativas P2b/P3.

### Envía a

- Diff vs goldens.

### Notas de implementación observadas en el código

Floats a 6 decimales por ruido f32.
