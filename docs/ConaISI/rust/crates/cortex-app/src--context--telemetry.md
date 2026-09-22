# src/context/telemetry.rs

## Qué tiene adentro

Log JSONL append-only `.cortex/enrichment-events.jsonl`, rotación a `.1.jsonl` a 5 MB. Fallos de persistencia no abortan.

`EnrichmentEvent`, `CitationEvent`, `PersistentObserver`, `new_run_id()`, `detect_citations(body, items_offered)`, `make_observer`, `offered_of(item) -> Pj`.

## Para qué sirve

Observabilidad de qué se ofreció y qué se citó, sin romper el pipeline.

## Relaciones

### Recibe de

- Bundles/items y texto posterior (citas).

### Envía a

- Archivo JSONL bajo `.cortex/`.

### Notas de implementación observadas en el código

Rotación 5 MB igual que el feedback del companion (mismo patrón de tamaño).
