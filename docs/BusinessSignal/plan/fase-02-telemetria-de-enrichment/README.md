# Fase 2 - Telemetria de Enrichment

**Fuente:** `docs/BusinessSignal/plan/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion de la fase

Esta fase conecta BusinessSignal con el ContextEnricher. Cada vez que Cortex ejecuta un enrichment, se captura un evento liviano sin duplicar contenido del vault.

Al terminar, documentar en `REALIZACION.md`.

## Nota obligatoria para agentes implementadores

### Reglas generales

- **No improvises.** Solo agrega el sink al enricher; no modifiques la logica de retrieval.
- **No saltees tests.** Gate de salida obligatorio.
- **No guardes contenido** en los eventos. Solo metadata y referencias.

### Aplicacion especifica

- El cambio al enricher debe ser MINIMO: agregar un atributo `_telemetry_sink` opcional y una llamada al final de `enrich()`.
- Si el sink es None, no hay overhead alguno.
- El sink debe ser fire-and-forget: si falla, loguear warning y continuar.
- NO cambiar la firma publica de `ContextEnricher.enrich()`.

## Plan operativo

### Archivos a crear

```text
cortex/business_signal/telemetry.py
cortex/business_signal/stores/event_store.py
tests/unit/business_signal/test_telemetry.py
tests/unit/business_signal/test_event_store.py
```

### Archivo a tocar

```text
cortex/context_enricher/enricher.py
```

### Detalle: `telemetry.py`

```python
"""cortex.business_signal.telemetry — Telemetry capture from enrichments."""

from __future__ import annotations
import logging
from typing import Protocol
from cortex.business_signal.models import EnrichmentEvent, EnrichmentHitRef

logger = logging.getLogger(__name__)


class TelemetrySink(Protocol):
    """Protocol for telemetry backends."""
    def record(self, event: EnrichmentEvent) -> None: ...


def build_enrichment_event(
    enriched_context,  # EnrichedContext
    work_context,      # WorkContext
    project_id: str,
    session_id: str | None = None,
    client_id: str | None = None,
    work_item_id: str | None = None,
    sprint_id: str | None = None,
) -> EnrichmentEvent:
    """Convert an EnrichedContext into a lightweight EnrichmentEvent.

    CRITICAL: This function must NOT copy content from items.
    Only metadata, scores, and references.
    """
    hits = []
    for item in enriched_context.items:
        hits.append(EnrichmentHitRef(
            source=item.source,
            source_id=item.source_id,
            title=item.title[:200],  # truncate title, never full content
            score=item.score,
            enriched_score=item.enriched_score,
            matched_by=item.matched_by,
            files_mentioned=item.files_mentioned,
            tags=item.tags,
            memory_type=getattr(item, 'memory_type', None),
            date=item.date,
            origin_scope=getattr(item, 'origin_scope', 'unknown'),
            origin_project_id=getattr(item, 'origin_project_id', None),
            origin_vault=getattr(item, 'origin_vault', None),
            vault_path=item.source_id if item.source == "semantic" else None,
        ))

    return EnrichmentEvent(
        event_id=f"evt_{uuid4().hex[:12]}",
        timestamp=datetime.now(timezone.utc),
        session_id=session_id,
        current_project_id=project_id,
        current_client_id=client_id,
        current_work_item_id=work_item_id,
        current_sprint_id=sprint_id,
        source=work_context.source,
        detected_domain=work_context.detected_domain,
        domain_confidence=work_context.domain_confidence,
        changed_files=work_context.changed_files,
        keywords=work_context.keywords[:20],
        search_queries=work_context.search_queries,
        total_searches=enriched_context.total_searches,
        total_raw_hits=enriched_context.total_raw_hits,
        total_items=enriched_context.total_items,
        total_chars=enriched_context.total_chars,
        within_budget=enriched_context.within_budget,
        hits=hits,
    )
```

### Detalle: `stores/event_store.py`

```python
"""Typed wrapper around JsonlStore for EnrichmentEvents."""

class EnrichmentEventStore:
    def __init__(self, workspace_root: Path, max_events: int = 5000):
        path = workspace_root / "business-signal" / "enrichment-events.jsonl"
        self._store = JsonlStore(path, max_lines=max_events)

    def record(self, event: EnrichmentEvent) -> None:
        self._store.append(event)
        self._store.rotate()

    def load_all(self) -> list[EnrichmentEvent]:
        return self._store.load_all(EnrichmentEvent)

    def load_filtered(self, filter: EventFilter) -> list[EnrichmentEvent]:
        events = self.load_all()
        # Apply filters...
        return filtered

    def count(self) -> int:
        return self._store.count()
```

`EnrichmentEventStore` implementa `TelemetrySink` protocol.

### Detalle: cambio en enricher.py

Al inicio de `ContextEnricher.__init__`:

```python
def __init__(
    self,
    episodic,
    semantic,
    config=None,
    telemetry_sink=None,  # NUEVO: optional TelemetrySink
):
    self.episodic = episodic
    self.semantic = semantic
    self.config = config or ContextEnricherConfig()
    self._telemetry_sink = telemetry_sink  # NUEVO
```

Al final de `ContextEnricher.enrich()`, DESPUES del return statement, no es posible. Entonces ANTES del return:

```python
    # Phase 7: Emit telemetry (optional, fire-and-forget)
    if self._telemetry_sink is not None:
        try:
            from cortex.business_signal.telemetry import build_enrichment_event
            event = build_enrichment_event(
                enriched_context=EnrichedContext(
                    work=work, items=budget_items,
                    total_searches=len(strategy_results),
                    total_raw_hits=total_raw_hits,
                    total_items=len(budget_items),
                    total_chars=total_chars,
                    within_budget=total_chars <= self.config.max_chars,
                ),
                work_context=work,
                project_id=getattr(self, '_project_id', '') or '',
            )
            self._telemetry_sink.record(event)
        except Exception as exc:
            logger.debug("BusinessSignal telemetry failed (non-fatal): %s", exc)

    return EnrichedContext(...)
```

**CRITICO para el implementador:**
- El import de `business_signal` es lazy (dentro del try).
- Si `business_signal` no esta instalado, NO falla.
- El try/except garantiza que un error de telemetria NUNCA rompe el enrichment.
- Performance: la telemetria no debe agregar mas de 1ms al enrichment.

### Checklist

- [ ] `build_enrichment_event()` no copia content de los items.
- [ ] `EnrichmentEventStore` implementa TelemetrySink protocol.
- [ ] `EnrichmentEventStore.record()` escribe JSONL y rota.
- [ ] `ContextEnricher` acepta `telemetry_sink` opcional.
- [ ] Si `telemetry_sink` es None, no hay overhead.
- [ ] Si telemetry falla, el enrichment continua normalmente.
- [ ] Import de `business_signal` es lazy dentro del try.
- [ ] Tests existentes del enricher siguen pasando sin telemetry_sink.
- [ ] Tests nuevos verifican que se emite evento con sink mock.
- [ ] Tests verifican que el evento no contiene content completo.

### Gate de salida

- `pytest tests/unit/business_signal/test_telemetry.py` pasa.
- `pytest tests/unit/context_enricher/` pasa (regresion).
- Al ejecutar enrichment con sink mock, se captura un EnrichmentEvent valido.
- El evento NO contiene el campo `content` de ningun item.

---
