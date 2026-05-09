# Fase 7 - Feedback Loop

**Fuente:** `docs/BusinessSignal/plan/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion

Implementa el ciclo de feedback para que BusinessSignal aprenda si las senales fueron utiles. Debe integrarse con `feedback_loop.py` existente donde sea posible. Al terminar, documentar en `REALIZACION.md`.

## Reglas para agentes

- No duplicar la funcionalidad de `cortex/feedback_loop.py`. Reutilizar patrones.
- SignalFeedback es distinto de MemoryFeedback: uno evalua senales, el otro memorias.
- El feedback debe ajustar scoring de senales futuras.

## Archivos a crear

```text
cortex/business_signal/feedback.py
cortex/business_signal/stores/feedback_store.py
tests/unit/business_signal/test_feedback.py
```

## Detalle: feedback.py

```python
class SignalFeedbackService:
    """Manages feedback for BusinessSignal signals."""

    def record(self, feedback: SignalFeedback) -> None:
        """Record feedback and update signal status if needed."""
        ...

    def get_feedback_for_signal(self, signal_id: str) -> list[SignalFeedback]:
        ...

    def calculate_false_positive_rate(self, detector_type: str) -> float:
        """Calculate false positive rate for a detector type."""
        ...

    def adjust_scoring_weights(self, detector_type: str) -> dict[str, float]:
        """Suggest weight adjustments based on accumulated feedback."""
        ...
```

Reglas:
- Si una senal recibe feedback `false_positive`, bajar su confidence.
- Si una senal recibe feedback `acted_on`, reforzar senales similares futuras.
- Si un detector tiene >30% false_positive rate, emitir warning en doctor.

## Checklist

- [ ] `SignalFeedbackService.record()` persiste en JSONL.
- [ ] Feedback `false_positive` actualiza status de la senal.
- [ ] `calculate_false_positive_rate()` calcula correctamente.
- [ ] CLI `cortex signals feedback` usa este servicio.
- [ ] MCP `cortex_record_signal_feedback` usa este servicio.
- [ ] Tests cubren todos los tipos de feedback.

## Gate de salida

- `pytest tests/unit/business_signal/test_feedback.py` pasa.
- Feedback se registra y puede consultarse por signal_id.

---
