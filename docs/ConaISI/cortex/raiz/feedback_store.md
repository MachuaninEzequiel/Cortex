# cortex/feedback_store.py

## Qué tiene adentro

- `FeedbackStore(directory, filename="feedback.jsonl", max_bytes=5MB)`.
- Append-only JSONL. Completa `ts` ISO si falta. `flush` + `fsync`. Nunca explota (OSError → warning).
- Rotación: si supera `max_bytes`, renombra a `*.1.jsonl` (una generación).
- `load()` lee archivo actual + rotado; líneas corruptas se saltan.

Formato de evento documentado en el módulo: `ts`, `type`, `memory_id`, `feedback_type`, `source`.

## Para qué sirve

Persistir feedback del ActionEngine/TUI que antes era solo in-memory (`FeedbackCollector`).

## Relaciones

### Recibe de

- Eventos dict desde `feedback_loop` / TUI (TYPE_CHECKING en feedback_loop).
- Directorio típicamente bajo `.cortex/`.

### Envía a

- Archivo `.cortex/feedback.jsonl` (y `.1.jsonl`).
- Consumidores que llaman `load()` para aprendizaje.

---
Fuente: lectura completa de `cortex/feedback_store.py`. No se usó documentación previa.
