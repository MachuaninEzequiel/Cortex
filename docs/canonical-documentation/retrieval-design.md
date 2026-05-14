# Retrieval Design - Filtros Estructurales, Boost por Intent, Presenter Agrupado

**Documento:** diseno completo de la capa de recuperacion (Capa 6)
**Audiencia:** implementadores
**Estado:** especificacion normativa

---

## 1. Objetivos

1. **Permitir filtros estructurales** en el enricher (por `doc_type`, `status`, `tags`, `vault_scope`, `max_age_days`).
2. **Boostear recuperacion por relevancia de tipo** segun intent detectado.
3. **Agrupar resultados por `doc_type`** en el presenter para reducir ruido cognitivo.
4. **Extender intent detector** con tipos especificos del dominio (decision, architecture, runbook, incident, history, recent).
5. **Telemetria persistida** que registra que se ofrecio, que se uso, por que.

---

## 2. Cambios en `EnrichedItem`

`EnrichedItem` necesita campos para que los filtros funcionen.

```python
# cortex/models.py - EXTENSION

from cortex.documentation.doc_type import DocType

class EnrichedItem(BaseModel):
    # Existentes
    source: str                    # "episodic" | "semantic"
    source_id: str
    title: str
    content: str
    score: float
    enriched_score: float
    matched_by: list[str]
    files_mentioned: list[str]
    date: datetime | None = None
    tags: list[str] = Field(default_factory=list)

    # NUEVOS
    doc_type: DocType | None = None              # None para items episodicos sin tipo
    status: str | None = None                    # heredado de frontmatter
    vault_scope: str = "local"                   # "local" | "enterprise"
    matched_chunk_id: str | None = None          # si el item viene de un chunk
    matched_section_title: str | None = None
    origin_project_id: str | None = None         # multi-proyecto enterprise
```

### Backwards compatibility

Items episodicos no tienen `doc_type` natural. Para evitar romper:
- `doc_type: DocType | None = None`.
- Filtros tratan `None` como "comodín" salvo que `doc_types` este explicitamente seteado.

---

## 3. `EnrichmentFilters` - Filtros estructurales

### 3.1 Modulo

```text
cortex/context_enricher/
    filters.py            # NUEVO
```

### 3.2 Contrato

```python
# cortex/context_enricher/filters.py
from pydantic import BaseModel, Field
from cortex.documentation.doc_type import DocType

class EnrichmentFilters(BaseModel):
    """Filtros estructurales para enrich()."""

    # Filtros por tipo
    doc_types: list[DocType] | None = None       # None = sin filtro
    exclude_doc_types: list[DocType] = Field(default_factory=list)

    # Filtros por status
    statuses_allowed: list[str] | None = None
    statuses_excluded: list[str] = Field(default_factory=list)

    # Filtros por tags
    tags_required: list[str] = Field(default_factory=list)   # AND
    tags_excluded: list[str] = Field(default_factory=list)
    tags_any_of: list[str] = Field(default_factory=list)     # OR

    # Filtros por scope
    vault_scope: str = "all"                       # "local" | "enterprise" | "all"

    # Filtros temporales
    max_age_days: int | None = None                # None = sin limite

    # Filtros por proyecto (enterprise)
    project_ids: list[str] | None = None

    # Comportamiento
    strict: bool = False                            # si True, items sin doc_type se excluyen


def apply_filters(items: list[EnrichedItem], filters: EnrichmentFilters) -> list[EnrichedItem]:
    """Apply filters to a list of items. Returns filtered list.

    Filters are AND-composed: an item must pass all enabled filters.
    """
```

### 3.3 Semantica de filtros

**Caso default (filters=None o vacios):**
- Sin filtro. Comportamiento actual.

**Caso `doc_types=[ADR, RUNBOOK]`:**
- Solo items con `doc_type in [ADR, RUNBOOK]`.
- Items con `doc_type=None`:
  - Si `strict=False`: incluidos (no se puede afirmar que NO son ADR/RUNBOOK).
  - Si `strict=True`: excluidos.

**Caso `tags_required=[security, auth]`:**
- Item debe tener AMBOS tags.

**Caso `tags_any_of=[bug, incident]`:**
- Item debe tener AL MENOS UNO de esos tags.

**Caso `max_age_days=30`:**
- Item debe tener `date >= now - 30d`.
- Items sin `date` se incluyen (no se puede juzgar).

**Caso `vault_scope="local"`:**
- Solo items con `vault_scope == "local"`.
- Para vaults solo locales: sin efecto.

### 3.4 Donde se aplica en el pipeline

```python
# cortex/context_enricher/enricher.py - EXTENSION

def enrich(
    work: WorkContext,
    *,
    filters: EnrichmentFilters | None = None,
    top_k: int | None = None,
) -> EnrichedContext:
    # ... Phase 1-2 (strategies, build items) sin cambio ...

    # Phase 2.5: FILTROS ESTRUCTURALES (NUEVO)
    if filters is not None:
        all_items = {sid: item for sid, item in all_items.items()
                     if _passes_filters(item, filters)}

    # ... Phase 3-4 (boosts) sin cambio ...

    # Phase 4.5: BOOST POR INTENT (NUEVO)
    intent = self._intent_detector.detect(work.search_queries[0] if work.search_queries else "")
    for item in all_items.values():
        if item.doc_type:
            route = resolve_route(item.doc_type)
            boost = route.retrieval_boost_per_intent.get(intent.value, 1.0)
            item.enriched_score *= boost

    # ... Phase 5-6 (threshold, sort, budget) sin cambio ...

    # Phase 7: TELEMETRIA (NUEVO)
    self._observer.record_enrichment(ctx, intent, filters)

    return ctx
```

---

## 4. `QueryIntent` extendido + boost por tipo

### 4.1 Extension del intent detector

Hoy `QueryIntentDetector` distingue `episodic` vs `semantic`. Extension:

```python
# cortex/retrieval/query_intent.py - EXTENSION

class QueryIntent(str, Enum):
    # Existentes
    EPISODIC = "episodic"
    SEMANTIC = "semantic"

    # NUEVOS
    DECISION = "decision"              # "por que decidimos X"
    ARCHITECTURE = "architecture"      # "como esta diseniado X"
    RUNBOOK = "runbook"                 # "como arranco X"
    INCIDENT = "incident"               # "que paso con X"
    POSTMORTEM = "postmortem"           # "root cause de X"
    HISTORY = "history"                 # "que hicimos sobre X"
    RECENT = "recent"                   # "ultimo cambio en X"
    SPEC = "spec"                       # "que requiere X"


class QueryIntentDetector:
    def detect(self, query: str) -> QueryIntent:
        """Detect intent from query.

        Heuristic-based: pattern matching on keywords.
        Future: LLM-based or learned classifier.
        """
```

### 4.2 Reglas heuristicas iniciales

| Pattern (case-insensitive) | Intent |
|---|---|
| `por que`, `razon`, `decidimos`, `decision` | DECISION |
| `arquitectura`, `diseno`, `componentes`, `arquitecto` | ARCHITECTURE |
| `como arranco`, `como deploy`, `procedimiento`, `runbook`, `steps to` | RUNBOOK |
| `incidente`, `caida`, `bug`, `error`, `falla` | INCIDENT |
| `root cause`, `postmortem`, `por que fallo`, `que salio mal` | POSTMORTEM |
| `que hicimos`, `historia`, `cuando empezamos` | HISTORY |
| `ultimo`, `reciente`, `hoy`, `esta semana` | RECENT |
| `spec`, `requisitos`, `que necesita` | SPEC |
| menciona `bug-#`, `PR-#`, fecha especifica | EPISODIC |
| Sin pattern especifico | SEMANTIC |

### 4.3 Aplicacion del boost

```python
def apply_intent_boost(item: EnrichedItem, intent: QueryIntent) -> float:
    """Apply boost based on item's doc_type and query intent."""
    if not item.doc_type:
        return item.enriched_score   # sin boost si tipo desconocido
    route = resolve_route(item.doc_type)
    boost = route.retrieval_boost_per_intent.get(intent.value, 1.0)
    return item.enriched_score * boost
```

### 4.4 Ejemplo: query "como arranco el server"

1. Intent detector: `RUNBOOK`.
2. Enricher recupera items (no filtra).
3. Boost: runbooks * 2.5, sessions * 1.0, ADRs * 1.0.
4. Top-5 final: 4 runbooks + 1 ADR.

### 4.5 Ejemplo: query "por que elegimos GraphQL"

1. Intent detector: `DECISION`.
2. Boost: ADRs * 2.0, decisions * 1.5, architecture * 1.5.
3. Top-5 final: 3 ADRs + 1 decision + 1 architecture doc.

---

## 5. `GroupedPresenter` - Agrupacion por DocType

### 5.1 Modulo

```text
cortex/context_enricher/
    presenter.py          # EXTENDIDO
```

### 5.2 Contrato

```python
# cortex/context_enricher/presenter.py - EXTENSION

class ContextPresenter:
    # Existentes
    def to_markdown(self, ctx: EnrichedContext) -> str: ...
    def to_compact(self, ctx: EnrichedContext) -> str: ...
    def to_json(self, ctx: EnrichedContext) -> str: ...

    # NUEVOS
    def to_markdown_grouped(self, ctx: EnrichedContext) -> str:
        """Markdown agrupado por doc_type."""

    def to_compact_grouped(self, ctx: EnrichedContext) -> str:
        """Compact agrupado por doc_type."""
```

### 5.3 Algoritmo de agrupacion

```python
def to_markdown_grouped(self, ctx: EnrichedContext) -> str:
    groups: dict[DocType | None, list[EnrichedItem]] = defaultdict(list)
    for item in ctx.items:
        groups[item.doc_type].append(item)

    # Ordenar grupos por max score
    ordered_groups = sorted(
        groups.items(),
        key=lambda kv: max(i.enriched_score for i in kv[1]),
        reverse=True,
    )

    out = []
    out.append(f"# Context Enrichment ({ctx.total_items} items, {ctx.total_chars} chars)\n")
    for doc_type, items in ordered_groups:
        type_label = doc_type.value.upper() if doc_type else "OTHER"
        out.append(f"\n## {type_label} ({len(items)} items)\n")
        for item in items:
            out.append(self._format_item_compact(item))
    return "\n".join(out)
```

### 5.4 Output ejemplo

```markdown
# Context Enrichment (6 items, 1845 chars)

## RUNBOOK (3 items)

### deploy-vault-canonical (score: 0.82)
**Tags:** deploy, runbook
**Matched by:** topic_search, keyword_search
**Section:** Procedure
Steps to deploy the canonical vault layout: 1. ...

### incident-response-auth (score: 0.71)
...

### rollback-after-migration (score: 0.65)
...

## ADR (2 items)

### ADR-007-onnx-embeddings (score: 0.88)
**Tags:** embedding, performance
**Matched by:** topic_search
**Section:** Decision
Adopt ONNX backend for embeddings because...

### ADR-001-hybrid-search-fusion (score: 0.61)
...

## SESSION (1 item)

### 2026-05-10_feat-add-routing-table (score: 0.55)
...
```

### 5.5 Razon del agrupado

Sin agrupar, el agente ve lista plana mezclada. Con agrupado:
- Sabe a primera vista que tipos de doc se encontraron.
- Puede ignorar grupos enteros si no son relevantes.
- Cita mas precisa ("segun el runbook X" vs "segun el item 3").

---

## 6. Telemetria de retrieval

### 6.1 `PersistentObserver`

```python
# cortex/context_enricher/telemetry.py - NUEVO

from pathlib import Path
import json
from datetime import datetime

class PersistentObserver:
    """Persists enrichment events to disk for later analysis."""

    def __init__(self, telemetry_path: Path):
        self._path = telemetry_path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def record_enrichment(
        self,
        ctx: EnrichedContext,
        intent: QueryIntent,
        filters: EnrichmentFilters | None,
    ) -> str:
        """Record an enrichment event. Returns run_id."""
        run_id = uuid.uuid4().hex[:12]
        event = {
            "run_id": run_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "intent": intent.value,
            "filters": filters.model_dump() if filters else None,
            "total_searches": ctx.total_searches,
            "total_raw_hits": ctx.total_raw_hits,
            "total_items": ctx.total_items,
            "total_chars": ctx.total_chars,
            "items_offered": [
                {
                    "source_id": item.source_id,
                    "doc_type": item.doc_type.value if item.doc_type else None,
                    "score": item.score,
                    "enriched_score": item.enriched_score,
                    "matched_by": item.matched_by,
                    "vault_scope": item.vault_scope,
                }
                for item in ctx.items
            ],
        }
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
        return run_id

    def record_citation(self, run_id: str, source_id: str) -> None:
        """Record that an item was actually used (cited) by the agent."""
        # Append to same file with event_type=citation
        ...

    def aggregate(self, since_days: int = 30) -> dict:
        """Aggregate events to compute hit rate, distribution, etc."""
        ...
```

### 6.2 `cortex_telemetry` en frontmatter de session

Ver `frontmatter-schema.md` seccion 5.3.

El `enricher_run_id` se genera al inicio del enrichment. Al cerrar la session:
1. Parse del body para extraer wiki-links: `[[<note>]]`.
2. Cross-reference con `items_offered`: `used = links INTERSECT offered`.
3. Calculo de hit_rate, by_type, by_strategy.
4. Inyeccion en frontmatter de la session note.

### 6.3 Comando `cortex memory-report`

```bash
$ cortex memory-report --since 30d --json
{
  "window": "2026-04-14 to 2026-05-14",
  "total_enrichments": 142,
  "total_citations": 89,
  "hit_rate": 0.627,
  "by_type": {
    "adr": {"offered": 67, "used": 41, "hit_rate": 0.612},
    "runbook": {"offered": 23, "used": 18, "hit_rate": 0.783},
    "session": {"offered": 95, "used": 22, "hit_rate": 0.232},
    "incident": {"offered": 8, "used": 6, "hit_rate": 0.750}
  },
  "by_strategy": {
    "topic_search": {"offered": 88, "used": 51},
    "entity_search": {"offered": 34, "used": 22},
    "file_search": {"offered": 67, "used": 12},
    "keyword_search": {"offered": 45, "used": 4}
  },
  "by_intent": {
    "decision": {"runs": 23, "avg_hit_rate": 0.78},
    "runbook": {"runs": 15, "avg_hit_rate": 0.82},
    "history": {"runs": 41, "avg_hit_rate": 0.54}
  },
  "latency": {
    "p50_ms": 187,
    "p95_ms": 412,
    "p99_ms": 891
  }
}
```

### 6.4 Privacidad y opt-out

- Default: telemetria habilitada para vault local.
- Default: telemetria deshabilitada para vault enterprise (privacidad).
- Opt-in/opt-out via `config.yaml`:
  ```yaml
  retrieval:
    telemetry:
      enabled: true
      include_content_excerpts: false   # nunca guardar contenido
      retention_days: 90
  ```

---

## 7. Integracion con BusinessSignal

La telemetria de retrieval alimenta a BusinessSignal:
- `PersistentObserver.event` se duplica al `EnrichmentTelemetryStore` de BusinessSignal.
- BusinessSignal puede leer `.cortex/enrichment-events.jsonl` directamente.

Sin duplicacion de datos, sin acoplamiento fuerte.

---

## 8. Cambios en API publica

### 8.1 `ContextEnricher.enrich()` signature

```python
def enrich(
    self,
    work: WorkContext,
    *,
    filters: EnrichmentFilters | None = None,    # NUEVO opcional
    top_k: int | None = None,
) -> EnrichedContext: ...
```

Default `filters=None` -> comportamiento actual.

### 8.2 `cortex search` CLI

```bash
$ cortex search "como arranco el server" \
    --doc-type runbook \
    --doc-type architecture \
    --max-age 90d \
    --scope local
```

### 8.3 MCP tool `cortex_search`

```python
@mcp.tool()
def cortex_search(
    query: str,
    doc_types: list[str] | None = None,
    statuses: list[str] | None = None,
    tags_required: list[str] | None = None,
    max_age_days: int | None = None,
    scope: str = "all",
    top_k: int = 5,
) -> dict: ...
```

Subagente documenter puede invocar:

```python
cortex_search(
    query="how does authentication work",
    doc_types=["adr", "architecture"],
    scope="local",
)
```

---

## 9. Tests obligatorios

```python
# tests/unit/context_enricher/test_filters.py

def test_no_filters_returns_all():
    """Items list unchanged when filters=None."""

def test_doc_types_filter():
    """Only items matching doc_types remain."""

def test_strict_excludes_none_doc_type():
    """strict=True excludes items without doc_type."""

def test_tags_required_all_must_match():
    """tags_required is AND-composed."""

def test_tags_any_of_one_must_match():
    """tags_any_of is OR-composed."""

def test_max_age_excludes_old():
    """Items older than max_age_days excluded."""

def test_vault_scope_local_only():
    """Only local items pass scope=local."""

def test_combined_filters_AND():
    """Multiple filters are AND-composed."""

def test_filter_preserves_score():
    """Filtered items keep original score."""


# tests/unit/context_enricher/test_intent_boost.py

def test_boost_by_intent_decision():
    """ADR items boosted 2x with intent=decision."""

def test_no_boost_for_unknown_intent():
    """Boost factor 1.0 for missing intent in routing."""

def test_boost_skipped_if_no_doc_type():
    """Items without doc_type get no boost."""


# tests/unit/context_enricher/test_grouped_presenter.py

def test_grouped_markdown_orders_by_max_score():
    """Group with highest-scoring item appears first."""

def test_grouped_markdown_other_for_none_doc_type():
    """Items without doc_type land in 'OTHER' group."""

def test_grouped_compact_compact_per_item():
    """Each item in grouped compact is one section."""


# tests/unit/context_enricher/test_telemetry.py

def test_record_enrichment_appends_jsonl():
    """record_enrichment writes one line per event."""

def test_record_citation_separate_event():
    """record_citation appends with event_type=citation."""

def test_aggregate_computes_hit_rate():
    """aggregate() returns correct hit_rate."""

def test_aggregate_by_type():
    """aggregate breaks down by doc_type."""

def test_telemetry_opt_out_via_config():
    """If config disabled, no file written."""
```

---

## 10. Configuracion

```yaml
# config.yaml - seccion retrieval
retrieval:
  filters:
    default_doc_types: null         # null = sin filtro default
    default_scope: local
    strict_doc_type: false
  intent:
    detector: heuristic              # heuristic | llm-based (futuro)
    boost_enabled: true
  presenter:
    default: markdown_grouped        # markdown | compact | markdown_grouped | compact_grouped | json
  telemetry:
    enabled: true
    path: .cortex/enrichment-events.jsonl
    include_content_excerpts: false
    retention_days: 90
```

---

## 11. Migracion del estado actual

### 11.1 EnrichedItem extension backwards-compatible

Agregar campos opcionales no rompe nada. Items existentes en pruebas pasan sin tocar.

### 11.2 Filtros opt-in

`enrich()` con `filters=None` mantiene comportamiento actual. Cero impacto en consumidores existentes.

### 11.3 Intent detector extension

Nuevos intents son adicionales; los existentes (`EPISODIC`, `SEMANTIC`) no cambian.

### 11.4 Presenter agrupado opt-in

`to_markdown` actual no cambia. `to_markdown_grouped` es nuevo.

---

## 12. Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| Filtros agresivos reducen coverage | Default None (sin filtro); telemetria reporta items filtrados |
| Boost por intent distorsiona ranking | A/B test; boost configurable; rollback facil |
| Heuristica de intent es fragil | Tests con corpus de queries reales; expansion gradual |
| Telemetria infla disco | Retention policy + rotation; default 90 dias |
| Presenter agrupado confunde al agente | Mantener flat presenter disponible; agrupado opt-in |
| Backwards compat de tests existentes | Schema extension solo agrega campos opcionales |

---

## 13. Metricas a monitorear

| Metrica | Definicion | Objetivo |
|---|---|---|
| Hit rate global | citations / offered | >= 70% |
| Hit rate por tipo | citations / offered por DocType | ADR >= 50%, runbook >= 40% |
| Filter coverage drop | drop% al aplicar filtros | <= 30% para no perder utilidad |
| Intent classification accuracy | manual sample | >= 80% |
| Presenter grouped acceptance | sessions usando grouped vs flat | preferencia revealed |
| Telemetria disk usage | bytes/dia | <10MB/dia para vault tipico |
