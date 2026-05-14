# Fase 05 - Telemetria In-Vault

**Fuente:** `docs/canonical-documentation/README.md`
**Estado:** Completada (2026-05-14) - ver [`REALIZACION.md`](REALIZACION.md)
**Esfuerzo estimado:** 1 dia (real: ~1 hora)
**Riesgo:** bajo
**Dependencias:** Fase 04

---

## 1. Objetivo

Implementar el **Mecanismo 1** acordado: telemetria in-vault que mide si el enricher rinde.

Componentes:
1. `PersistentObserver` que persiste eventos de enrichment a `.cortex/enrichment-events.jsonl`.
2. Campo `cortex_telemetry` en frontmatter de session note.
3. Comando `cortex memory-report` extendido con metricas por DocType, strategy, intent.
4. Integracion con `ContextEnricher` via callback opcional.

Sin esto, todas las decisiones futuras sobre el enricher son ciegas.

---

## 2. Archivos a crear / tocar

```text
cortex/context_enricher/
    telemetry.py                   # NUEVO: PersistentObserver, EnrichmentEvent
    enricher.py                    # EXTENDIDO: invoca observer al final

cortex/documentation/
    schemas/session.py             # EXTENDIDO: CortexTelemetry sub-model

cortex/cli/
    memory_report.py               # NUEVO: cortex memory-report extendido

cortex/services/
    session_service.py             # EXTENDIDO: acepta cortex_telemetry y lo escribe

config.yaml                          # template, agregar seccion retrieval.telemetry

tests/unit/context_enricher/
    test_telemetry.py
    test_enricher_with_telemetry.py

tests/unit/cli/
    test_memory_report.py

tests/integration/
    test_telemetry_e2e.py
```

---

## 3. Responsabilidades

### `telemetry.py`

```python
from pathlib import Path
from datetime import datetime, UTC
import json
import uuid
from cortex.documentation.doc_type import DocType
from cortex.context_enricher.filters import EnrichmentFilters
from cortex.retrieval.query_intent import QueryIntent

class PersistentObserver:
    """Persists enrichment events to JSONL for later analysis."""

    def __init__(self, telemetry_path: Path, enabled: bool = True):
        self._path = telemetry_path
        self._enabled = enabled
        if self._enabled:
            self._path.parent.mkdir(parents=True, exist_ok=True)

    def record_enrichment(
        self,
        ctx: EnrichedContext,
        intent: QueryIntent | None = None,
        filters: EnrichmentFilters | None = None,
        latency_ms: int | None = None,
    ) -> str:
        """Record an enrichment event. Returns run_id."""
        if not self._enabled:
            return ""

        run_id = uuid.uuid4().hex[:12]
        event = {
            "event_type": "enrichment",
            "run_id": run_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "intent": intent.value if intent else None,
            "filters": filters.model_dump() if filters else None,
            "latency_ms": latency_ms,
            "total_searches": ctx.total_searches,
            "total_raw_hits": ctx.total_raw_hits,
            "total_items": ctx.total_items,
            "total_chars": ctx.total_chars,
            "within_budget": ctx.within_budget,
            "items_offered": [
                {
                    "source_id": item.source_id,
                    "doc_type": item.doc_type.value if item.doc_type else None,
                    "score": item.score,
                    "enriched_score": item.enriched_score,
                    "matched_by": item.matched_by,
                    "vault_scope": item.vault_scope,
                    "tags": item.tags,
                }
                for item in ctx.items
            ],
        }
        self._append(event)
        return run_id

    def record_citation(self, run_id: str, source_id: str) -> None:
        """Record that an item was actually used (cited)."""
        if not self._enabled:
            return
        event = {
            "event_type": "citation",
            "run_id": run_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "source_id": source_id,
        }
        self._append(event)

    def aggregate(self, since_days: int = 30) -> dict:
        """Aggregate events to compute hit rate, distribution, etc."""
        # Read JSONL, filter by date, compute statistics
        ...

    def _append(self, event: dict) -> None:
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
```

### Extension del `ContextEnricher`

```python
# cortex/context_enricher/enricher.py - EXTENSION

class ContextEnricher:
    def __init__(self, ..., observer: PersistentObserver | None = None):
        # ...
        self._observer = observer

    def enrich(self, work: WorkContext, *, filters=None, top_k=None) -> EnrichedContext:
        import time
        t0 = time.perf_counter()

        # ... pipeline existente (Phase 1-6) ...

        ctx = EnrichedContext(...)

        # Phase 7: Telemetry (NUEVO)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        if self._observer:
            run_id = self._observer.record_enrichment(ctx, intent, filters, latency_ms)
            ctx.enricher_run_id = run_id   # nuevo campo en EnrichedContext

        return ctx
```

### Sub-model `CortexTelemetry`

Ya definido en `data-model.md`. Agregar a `SessionFrontmatter`:

```python
# cortex/documentation/schemas/session.py

class CortexTelemetry(BaseModel):
    enricher_run_id: str
    context_items_offered: int = Field(ge=0)
    context_items_used: int = Field(ge=0)
    context_hit_rate: float = Field(ge=0.0, le=1.0)
    context_by_type: dict[str, int] = Field(default_factory=dict)
    context_by_strategy: dict[str, int] = Field(default_factory=dict)
    context_by_scope: dict[str, int] = Field(default_factory=dict)
    enriched_score_p50: float = 0.0
    enriched_score_p95: float = 0.0
    enricher_latency_ms: int = 0
    filters_applied: dict | None = None


class SessionFrontmatter(CommonFrontmatter):
    doc_type: DocType = DocType.SESSION
    session_id: str
    pr: str | None = None
    branch: str | None = None
    commit: str | None = None
    cortex_telemetry: CortexTelemetry | None = None
```

### Inyeccion de `cortex_telemetry` al cerrar sesion

```python
# cortex/services/session_service.py - EXTENSION

class SessionService:
    def create(self, ..., cortex_telemetry: CortexTelemetry | None = None) -> Path:
        # Si no se pasa explicitamente, intentar computar desde observer
        if cortex_telemetry is None and self._observer:
            cortex_telemetry = self._build_telemetry_from_observer()

        data = SessionData(
            title=title,
            session_id=...,
            cortex_telemetry=cortex_telemetry,
            ...
        )
        path = write_session_note(data, vault=self._semantic)
        return path

    def _build_telemetry_from_observer(self) -> CortexTelemetry | None:
        """Build telemetry from the last enrichment run."""
        # Lee el ultimo enrichment event de la sesion actual
        # Parse body en busca de wiki-links para calcular `context_items_used`
        # Computa hit rate, by_type, by_strategy
        ...
```

### Comando `cortex memory-report`

```python
# cortex/cli/memory_report.py - NUEVO

import typer
from datetime import datetime, timedelta, UTC
import json

app = typer.Typer()

@app.command()
def report(
    since: str = typer.Option("30d", "--since"),
    json_output: bool = typer.Option(False, "--json"),
    by: list[str] = typer.Option(["type"], "--by"),
):
    """Generate retrieval telemetry report."""
    observer = _get_observer()
    days = _parse_since(since)
    aggregated = observer.aggregate(since_days=days)

    if json_output:
        typer.echo(json.dumps(aggregated, indent=2))
    else:
        _print_human_report(aggregated, by)
```

Output ejemplo en `retrieval-design.md` seccion 6.3.

### Config

```yaml
# config.yaml - agregar
retrieval:
  telemetry:
    enabled: true
    path: .cortex/enrichment-events.jsonl
    include_content_excerpts: false
    retention_days: 90
```

---

## 4. Calculo de items_used (citation detection)

Algoritmo para detectar items citados:

```python
def detect_citations(session_body: str, items_offered: list[dict]) -> list[str]:
    """Detect which offered items were actually cited in the session body.

    A citation is:
    - A wiki-link [[<note>]] matching an offered item's source_id (path).
    - A markdown link to a path inside the vault.
    - The literal string of an item title.
    """
    wiki_links = WIKI_LINK_RE.findall(session_body)
    md_links = MD_LINK_RE.findall(session_body)

    cited = []
    for item in items_offered:
        sid = item["source_id"]
        title = item.get("title", "")
        if any(link in sid for link in wiki_links + md_links):
            cited.append(sid)
        elif title and title in session_body:
            cited.append(sid)
    return cited
```

Heuristica imperfecta pero suficiente. Mejorable a futuro con AST de markdown.

---

## 5. Tests

### `test_telemetry.py`

```python
def test_record_enrichment_appends_jsonl(tmp_path)
def test_record_enrichment_returns_run_id(tmp_path)
def test_record_enrichment_disabled_no_file(tmp_path)
def test_record_citation_appends_separate_event(tmp_path)
def test_aggregate_empty_returns_zeros(tmp_path)
def test_aggregate_computes_hit_rate(tmp_path_with_events)
def test_aggregate_breakdown_by_type(tmp_path_with_events)
def test_aggregate_breakdown_by_strategy(tmp_path_with_events)
def test_aggregate_filters_by_window(tmp_path_with_events)
def test_observer_thread_safe()  # concurrent appends
def test_observer_handles_disk_error_gracefully(tmp_path)
def test_observer_log_format_stable(tmp_path)
```

### `test_enricher_with_telemetry.py`

```python
def test_enricher_records_event_when_observer_set()
def test_enricher_no_record_when_observer_none()
def test_enricher_includes_latency_in_event()
def test_enricher_run_id_propagated_to_ctx()
```

### `test_memory_report.py`

```python
def test_memory_report_human_format()
def test_memory_report_json_format()
def test_memory_report_since_window()
def test_memory_report_by_type_breakdown()
def test_memory_report_empty_db()
```

### `test_telemetry_e2e.py` (integration)

```python
def test_end_to_end_session_with_telemetry(tmp_vault, enricher_with_observer):
    """Run enrich -> create session -> verify cortex_telemetry in frontmatter."""

def test_citations_detected_from_body(tmp_vault, observer):
    """Body with wiki-link to offered item -> citation recorded."""

def test_aggregate_includes_recent_sessions(tmp_vault, observer):
    """memory-report includes today's sessions."""
```

---

## 6. Criterios de diseno

- **Telemetria es no bloqueante.** Falla del observer no aborta enrich.
- **Append-only JSONL.** Simple, robusto.
- **Opt-in via config.** Default ON local, OFF enterprise.
- **No guarda contenido.** Solo metadata.
- **Citation detection heuristica.** Imperfecta pero suficiente para MVP.
- **`cortex_telemetry` opcional** en frontmatter. Sessions sin telemetria son validas.

---

## 7. Checklist

- [x] `cortex/context_enricher/telemetry.py` con `PersistentObserver`
- [x] `ContextEnricher` acepta `observer` opcional
- [x] `CortexTelemetry` agregado a `SessionFrontmatter` (desde Fase 01)
- [x] `SessionService.create()` acepta y persiste `cortex_telemetry`
- [x] `cortex memory-report` extendido (`--telemetry`, `--since-days`)
- [x] Config con seccion `retrieval.telemetry` (cerrado en deuda post-Fase 06, ver `REALIZACION.md` seccion "Cierre de deuda")
- [x] Citation detection implementada
- [x] Tests: 23 nuevos en deuda (helper, CLI, E2E), 25 originales = 48 totales
- [x] Coverage 100% en `telemetry.py` (cierre completo, sin lineas defensive sin cubrir)
- [x] Helper `make_observer(workspace_layout, config=...)` en `telemetry.py`
- [x] Tests integration E2E (`tests/integration/test_telemetry_e2e.py`)
- [x] Tests CLI `cortex memory-report --telemetry` con CliRunner (4 tests)

---

## 8. Gate de salida

- `pytest tests/unit/context_enricher tests/unit/cli tests/integration/test_telemetry_e2e.py` pasa al 100%.
- Una session creada via `SessionService.create()` con observer activo tiene `cortex_telemetry` en frontmatter.
- `cortex memory-report --since 7d` retorna stats validos (o vacios si no hay events).
- Disabled telemetry no escribe archivo.
- `REALIZACION.md` documentado.

---

## 9. Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| Citation detection con false negatives | Aceptable; agrega valor incremental, no exacto |
| JSONL crece sin limite | Retention policy + rotacion |
| Performance overhead | Async append; benchmark verifica |
| Privacy en enterprise | Default OFF; opt-in via config |
| Tests no deterministicos por timestamps | Freeze time con `freezegun` |
| Observer falla y rompe enrich | try/except con log; no propagar |

---

## 10. Notas para agentes implementadores

1. **Empezar por `PersistentObserver`.** Pieza aislada, testeable.
2. **Integrar con enricher despues.** Callback simple.
3. **Citation detection puede empezar simple.** Mejorar iterativamente.
4. **`cortex_telemetry` es opcional.** No requerido en cada session.
5. **`memory-report` puede simular vacio si no hay events.**
6. **No saturar el log.** Solo eventos de alto nivel, no detalle.
7. **Mock time en tests.** `freeze_time` o `monkeypatch`.

---

## 11. Referencias

- `docs/canonical-documentation/retrieval-design.md` - especificacion completa Capa 6
- `docs/canonical-documentation/frontmatter-schema.md` seccion 5.3 - cortex_telemetry ejemplo
- `docs/BusinessSignal/plan/README.md` - BusinessSignal consume estos eventos
- `cortex/context_enricher/observer.py` - existente (extender o reemplazar)
