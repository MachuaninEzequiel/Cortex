# src/context/filters.rs

## Qué tiene adentro

`EnrichmentFilters` (campos opcionales). `apply_filters` / `apply_filters_at` recortan `EnrichedItem` por metadatos (doc_type, fechas, paths, etc.). `filters=None` o vacío = no-op.

## Para qué sirve

Quitar ítems irrelevantes POR METADATOS después del retrieval content-driven.

## Relaciones

### Recibe de

- Bundle/items y filtros del caller (P12A-7).

### Envía a

- Pipeline de contexto / checker `p12a7_check`.

### Notas de implementación observadas en el código

No altera scores; remueve ítems.
