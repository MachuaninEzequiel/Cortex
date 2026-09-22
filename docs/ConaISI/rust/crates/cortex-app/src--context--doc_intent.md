# src/context/doc_intent.rs

## Qué tiene adentro

`DocIntent` (capa distinta de QueryIntent). `DocIntentResult`. `detect_doc_intent(query)`. `retrieval_boost(doc_type, intent) -> f64` usando la tabla `RouteSpec.retrieval_boost_per_intent`.

## Para qué sirve

Multiplicar scores de documentos del vault según intención de la query (history/spec/incident/...).

## Relaciones

### Recibe de

- Query y `semantic::routing::DocType`.

### Envía a

- `ContextEnricher` (boost por item semántico).

### Notas de implementación observadas en el código

Dos capas ortogonales: QueryIntent pesa RRF entre fuentes; DocIntent pesa tipos dentro del vault.
