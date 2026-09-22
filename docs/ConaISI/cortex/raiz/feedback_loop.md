# cortex/feedback_loop.py

## Qué tiene adentro

- `ImplicitFeedback`: overlap keywords/files/entities → `usefulness_score`; `is_useful` si ≥ 0.3.
- `ExplicitFeedback`: source github/user/system, type positive/negative/neutral, score -1..1.
- Resto del archivo: `FeedbackCollector` (in-memory) que puede apoyarse en `FeedbackStore` (TYPE_CHECKING).

## Para qué sirve

Aprender qué recuerdos fueron útiles para boostear retrieval futuro y alimentar ActionEngine.

## Relaciones

### Recibe de

- Work context vs memorias recuperadas.
- Ratings explícitos.
- Opcional `FeedbackStore`.

### Envía a

- Scores/boosts a enricher/ActionEngine.
- Persistencia JSONL si hay store.

---
Fuente: lectura de `cortex/feedback_loop.py` (inicio). No se usó documentación previa.
