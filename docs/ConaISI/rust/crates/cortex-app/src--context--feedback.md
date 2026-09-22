# src/context/feedback.rs

## Qué tiene adentro

Puerto de ImplicitFeedbackAnalyzer. `ImplicitFeedback`. `procesar_feedback_implicito(...)` aplica boost implícito (config `implicit_boost` 0.15).

## Para qué sirve

Subir scores de items que el usuario «usó» implícitamente (clicks/citas), sin feedback explícito.

## Relaciones

### Recibe de

- Eventos/telemetría de uso y items candidatos.

### Envía a

- `ContextEnricher` si `feedback_loop`.

### Notas de implementación observadas en el código

Solo la parte que consume el enricher de `feedback_loop.py`, no el store completo de feedback.
