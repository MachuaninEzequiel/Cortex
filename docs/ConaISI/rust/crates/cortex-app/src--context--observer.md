# src/context/observer.rs

## Qué tiene adentro

`ContextObserver`. Fuentes: git diff, PR metadata, input manual. Extrae keywords, imports, functions, classes; detecta dominio; genera las 4 `search_queries`.

Helpers públicos: `extract_imports/functions/classes/keywords`, `extract_text_keywords`.

## Para qué sirve

Armar el `WorkContext` que alimenta `ContextEnricher::enrich`.

## Relaciones

### Recibe de

- Diff/PR/texto; `domain_detector`.

### Envía a

- `WorkContext` → enricher.

### Notas de implementación observadas en el código

P12A-7; el módulo P7 original no incluía observer.
