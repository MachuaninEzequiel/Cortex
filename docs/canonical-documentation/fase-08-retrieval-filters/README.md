# Fase 08 - Retrieval Filters

**Fuente:** `docs/canonical-documentation/README.md`
**Estado:** Pendiente de ejecucion
**Esfuerzo estimado:** 2 dias
**Riesgo:** medio
**Dependencias:** Fase 01, Fase 07

---

## 1. Objetivo

Implementar las sub-capas restantes de la **Capa 6 (Recuperacion consciente del schema)**:
- `EnrichmentFilters` (filtros estructurales en `enrich()`).
- `QueryIntent` extendido con tipos especificos (decision, runbook, etc).
- Boost por intent + DocType segun routing table.
- `GroupedPresenter` con output agrupado por DocType.
- Extension de `EnrichedItem` con `doc_type`, `status`, `vault_scope`.

---

## 2. Archivos a crear / tocar

```text
cortex/context_enricher/
    enricher.py                # EXTENDIDO: acepta filters, aplica boost
    filters.py                 # NUEVO: EnrichmentFilters + apply_filters
    presenter.py               # EXTENDIDO: GroupedPresenter

cortex/retrieval/
    query_intent.py            # EXTENDIDO: nuevos intents

cortex/models.py               # EXTENDIDO: EnrichedItem fields

cortex/mcp/
    server.py                  # EXTENDIDO: cortex_search tool con filtros

cortex/cli/
    search_command.py          # NUEVO o EXTENDIDO: cortex search con flags

tests/unit/context_enricher/
    test_filters.py
    test_enricher_filters.py
    test_intent_boost.py
    test_grouped_presenter.py

tests/unit/retrieval/
    test_query_intent.py

tests/integration/
    test_search_with_filters.py
```

---

## 3. Responsabilidades

### `filters.py`

```python
# cortex/context_enricher/filters.py
from pydantic import BaseModel, Field
from datetime import datetime, UTC, timedelta
from cortex.documentation.doc_type import DocType


class EnrichmentFilters(BaseModel):
    doc_types: list[DocType] | None = None
    exclude_doc_types: list[DocType] = Field(default_factory=list)
    statuses_allowed: list[str] | None = None
    statuses_excluded: list[str] = Field(default_factory=list)
    tags_required: list[str] = Field(default_factory=list)
    tags_excluded: list[str] = Field(default_factory=list)
    tags_any_of: list[str] = Field(default_factory=list)
    vault_scope: str = "all"
    max_age_days: int | None = None
    project_ids: list[str] | None = None
    strict: bool = False


def apply_filters(items: list[EnrichedItem], filters: EnrichmentFilters) -> list[EnrichedItem]:
    if filters is None:
        return items

    result = []
    for item in items:
        if _passes_filter(item, filters):
            result.append(item)
    return result


def _passes_filter(item: EnrichedItem, filters: EnrichmentFilters) -> bool:
    # doc_types
    if filters.doc_types is not None:
        if item.doc_type is None:
            if filters.strict:
                return False
        elif item.doc_type not in filters.doc_types:
            return False

    if item.doc_type in filters.exclude_doc_types:
        return False

    # status
    if filters.statuses_allowed and item.status not in filters.statuses_allowed:
        return False
    if item.status in filters.statuses_excluded:
        return False

    # tags
    item_tags = set(item.tags or [])
    if filters.tags_required and not set(filters.tags_required).issubset(item_tags):
        return False
    if filters.tags_excluded and item_tags & set(filters.tags_excluded):
        return False
    if filters.tags_any_of and not (item_tags & set(filters.tags_any_of)):
        return False

    # scope
    if filters.vault_scope != "all" and item.vault_scope != filters.vault_scope:
        return False

    # age
    if filters.max_age_days is not None and item.date is not None:
        cutoff = datetime.now(UTC) - timedelta(days=filters.max_age_days)
        if item.date < cutoff:
            return False

    # project
    if filters.project_ids and item.origin_project_id not in filters.project_ids:
        return False

    return True
```

### `query_intent.py` extension

```python
# cortex/retrieval/query_intent.py - EXTENSION

class QueryIntent(str, Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    DECISION = "decision"
    ARCHITECTURE = "architecture"
    RUNBOOK = "runbook"
    INCIDENT = "incident"
    POSTMORTEM = "postmortem"
    HISTORY = "history"
    RECENT = "recent"
    SPEC = "spec"


INTENT_PATTERNS: dict[QueryIntent, list[re.Pattern]] = {
    QueryIntent.DECISION: [
        re.compile(r"\bpor qu[eé]\b", re.I),
        re.compile(r"\brazon", re.I),
        re.compile(r"\bdecidim", re.I),
        re.compile(r"\bdecision", re.I),
        re.compile(r"\bwhy did", re.I),
    ],
    QueryIntent.ARCHITECTURE: [
        re.compile(r"\barquitectura", re.I),
        re.compile(r"\bdise[nñ]o", re.I),
        re.compile(r"\bcomponentes", re.I),
        re.compile(r"\barchitect", re.I),
    ],
    QueryIntent.RUNBOOK: [
        re.compile(r"\bcomo arranc", re.I),
        re.compile(r"\bcomo deploy", re.I),
        re.compile(r"\bprocedimiento", re.I),
        re.compile(r"\brunbook", re.I),
        re.compile(r"\bsteps to", re.I),
        re.compile(r"\bhow do I", re.I),
    ],
    QueryIntent.INCIDENT: [
        re.compile(r"\bincidente", re.I),
        re.compile(r"\bcaida", re.I),
        re.compile(r"\bbug", re.I),
        re.compile(r"\berror", re.I),
        re.compile(r"\bfalla", re.I),
        re.compile(r"\boutage", re.I),
    ],
    QueryIntent.POSTMORTEM: [
        re.compile(r"\broot cause", re.I),
        re.compile(r"\bpostmortem", re.I),
        re.compile(r"\bpor qu[eé] fall", re.I),
        re.compile(r"\bque sali[oó] mal", re.I),
    ],
    QueryIntent.HISTORY: [
        re.compile(r"\bque hicimos", re.I),
        re.compile(r"\bhistoria", re.I),
        re.compile(r"\bcuando empez", re.I),
    ],
    QueryIntent.RECENT: [
        re.compile(r"\bultimo", re.I),
        re.compile(r"\breciente", re.I),
        re.compile(r"\bhoy", re.I),
        re.compile(r"\besta semana", re.I),
        re.compile(r"\blatest", re.I),
        re.compile(r"\brecent", re.I),
    ],
    QueryIntent.SPEC: [
        re.compile(r"\bspec\b", re.I),
        re.compile(r"\brequisitos", re.I),
        re.compile(r"\bque necesita", re.I),
    ],
}


class QueryIntentDetector:
    def detect(self, query: str) -> QueryIntent:
        if not query:
            return QueryIntent.SEMANTIC

        # Episodic: marcas explicitas
        if re.search(r"#\d+|bug-\d+|PR-?\d+", query):
            return QueryIntent.EPISODIC

        # Test patterns en orden de prioridad
        for intent in [QueryIntent.POSTMORTEM, QueryIntent.INCIDENT, QueryIntent.RUNBOOK,
                       QueryIntent.DECISION, QueryIntent.ARCHITECTURE, QueryIntent.SPEC,
                       QueryIntent.RECENT, QueryIntent.HISTORY]:
            for pattern in INTENT_PATTERNS[intent]:
                if pattern.search(query):
                    return intent

        return QueryIntent.SEMANTIC
```

### Extension de `EnrichedItem`

```python
# cortex/models.py - EXTENSION

class EnrichedItem(BaseModel):
    # ... existentes
    doc_type: DocType | None = None
    status: str | None = None
    vault_scope: str = "local"
    matched_chunk_id: str | None = None
    matched_section_title: str | None = None
    origin_project_id: str | None = None
```

### Extension de `ContextEnricher`

```python
# cortex/context_enricher/enricher.py - EXTENSION

def enrich(
    self,
    work: WorkContext,
    *,
    filters: EnrichmentFilters | None = None,
    top_k: int | None = None,
) -> EnrichedContext:
    # Existing phases 1-4 ...

    # Phase 2.5: FILTROS ESTRUCTURALES (NUEVO)
    if filters is not None:
        all_items = {
            sid: item for sid, item in all_items.items()
            if _passes_filter(item, filters)
        }

    # Phase 3-4 (boost normal) ...

    # Phase 4.5: BOOST POR INTENT (NUEVO)
    if work.search_queries:
        intent = self._intent_detector.detect(work.search_queries[0])
        for item in all_items.values():
            if item.doc_type:
                route = resolve_route(item.doc_type)
                boost = route.retrieval_boost_per_intent.get(intent.value, 1.0)
                item.enriched_score *= boost

    # Phase 5-6 (threshold, sort, budget) ...

    # Phase 7: Telemetry (de Fase 05)
    ...

    return ctx
```

### `GroupedPresenter`

```python
# cortex/context_enricher/presenter.py - EXTENSION

class ContextPresenter:
    # existentes: to_markdown, to_compact, to_json

    def to_markdown_grouped(self, ctx: EnrichedContext) -> str:
        groups: dict[DocType | None, list[EnrichedItem]] = defaultdict(list)
        for item in ctx.items:
            groups[item.doc_type].append(item)

        ordered = sorted(
            groups.items(),
            key=lambda kv: max(i.enriched_score for i in kv[1]),
            reverse=True,
        )

        out = []
        out.append(f"# Context Enrichment ({ctx.total_items} items, {ctx.total_chars} chars)\n")
        for doc_type, items in ordered:
            label = doc_type.value.upper() if doc_type else "OTHER"
            out.append(f"\n## {label} ({len(items)} items)\n")
            for item in items:
                out.append(self._format_item(item))
        return "\n".join(out)

    def to_compact_grouped(self, ctx: EnrichedContext) -> str:
        """Same grouping but compact format."""
```

### CLI

```bash
$ cortex search "como arranco el server" \
    --doc-type runbook --doc-type architecture \
    --max-age 90d \
    --scope local \
    --presenter grouped
```

### MCP tool

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

---

## 4. Tests

Ver `testing-strategy.md` seccion 3.8 para detalle de cada test. Aplican:

### `test_filters.py` (>= 15 tests)
### `test_enricher_filters.py` (>= 5 tests integracion enricher + filters)
### `test_intent_boost.py` (>= 5 tests)
### `test_grouped_presenter.py` (>= 5 tests)
### `test_query_intent.py` (>= 12 tests, uno por intent + edge cases)
### `test_search_with_filters.py` (>= 5 integracion)

---

## 5. Checklist

- [ ] `cortex/context_enricher/filters.py` con `EnrichmentFilters` y `apply_filters`
- [ ] `cortex/retrieval/query_intent.py` extendido con 8 intents nuevos
- [ ] `cortex/context_enricher/enricher.py` aplica filters + boost
- [ ] `cortex/context_enricher/presenter.py` con `GroupedPresenter`
- [ ] `cortex/models.py` EnrichedItem extendido
- [ ] CLI `cortex search` con flags
- [ ] MCP `cortex_search` con filtros
- [ ] Tests >= 47
- [ ] Coverage >= 90%

---

## 6. Gate de salida

- `pytest tests/unit/context_enricher tests/unit/retrieval tests/integration/test_search_with_filters.py` pasa al 100%.
- Query "como arranco" + boost intent retorna runbooks primero.
- `cortex search --doc-type adr` filtra correctamente.
- Presenter agrupado tiene output legible.
- `REALIZACION.md` documentado.

---

## 7. Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| Heuristica de intent es fragil | Test corpus de queries reales; expansion gradual |
| Filtros restrictivos vacian resultados | strict=False default; advisory en CLI cuando 0 hits |
| Boost distorsiona ranking obvio | A/B test antes de habilitar default; flag para deshabilitar |
| EnrichedItem.doc_type=None mayoritario inicialmente | Default permisivo en filtros |
| Performance overhead filtros | Aplican post-RRF, sobre lista corta; despreciable |
| Presenter agrupado confunde al agente | Mantener flat como default; grouped opt-in |
| Multilingue (es/en) en patterns | Patterns para ambos idiomas |
| Test fragiles por patterns | Compilar regex una vez; tests verifican set known queries |

---

## 8. Notas para agentes implementadores

1. **Filtros opt-in default None.** Backwards compat absoluta.
2. **Patterns en regex compilados.** No re-compilar en cada call.
3. **Tests con corpus diverso de queries.** Bilingue.
4. **Boost configurable y rollback facil.** No hardcodear factors.
5. **Presenter grouped no es default obligatorio.** Opcion.
6. **MCP tool no rompe consumers existentes.** Args opcionales.

---

## 9. Referencias

- `docs/canonical-documentation/retrieval-design.md` - especificacion completa
- `docs/canonical-documentation/routing-table.md` - retrieval_boost_per_intent
- `cortex/context_enricher/enricher.py` - integracion
- `cortex/retrieval/query_intent.py` - intent detector base
