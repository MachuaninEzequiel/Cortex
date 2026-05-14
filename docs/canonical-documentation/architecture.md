# Arquitectura Objetivo - Las 6 Capas en Detalle

**Documento:** detalle tecnico de la arquitectura propuesta
**Audiencia:** implementadores y revisores
**Estado:** propuesta aprobada
**Fecha:** 2026-05-14

---

## Vista General

```text
+--------------------------------------------------------------+
| CAPA 6: Recuperacion consciente del schema + telemetria       |
|         filtros doc_type/status/tags · boost por intent ·     |
|         presenter agrupado · cortex_telemetry in-vault        |
|         observer persistido · cortex memory-report extendido  |
+--------------------------------------------------------------+
                              ^
+--------------------------------------------------------------+
| CAPA 5: Vectorizacion inteligente                             |
|         chunking H2/H3 · embedding con frontmatter ·          |
|         cache en disco por fingerprint · sync local<->ent ·  |
|         boost por tipo                                        |
+--------------------------------------------------------------+
                              ^
+--------------------------------------------------------------+
| CAPA 4: Writers canonicos write_*_note                        |
|         firma simetrica · validacion · index incremental ·    |
|         audit trail enterprise · templates Jinja              |
+--------------------------------------------------------------+
                              ^
+--------------------------------------------------------------+
| CAPA 3: Routing canonico DOC_TYPE_ROUTING                     |
|         subfolder · filename · template · writer · indexer ·  |
|         promotable · enterprise_subfolder · retrieval_boost   |
+--------------------------------------------------------------+
                              ^
+--------------------------------------------------------------+
| CAPA 2: Schema de frontmatter unificado                       |
|         comunes · enterprise · por tipo · pydantic validator  |
|         schema_version · fingerprint                          |
+--------------------------------------------------------------+
                              ^
+--------------------------------------------------------------+
| CAPA 1: DocType + dataclasses canonicas                       |
|         Enum cerrado 12 tipos MVP · dataclasses tipadas       |
+--------------------------------------------------------------+
```

Cada capa depende solo de capas inferiores. Cambios en capas superiores no afectan inferiores.

---

## CAPA 1: DocType como ciudadano de primera clase

### Responsabilidad

Definir la lista cerrada de tipos de documento y sus contratos de datos.

### Modulo

```text
cortex/documentation/
    __init__.py
    doc_type.py           # Enum DocType
    schemas/
        __init__.py
        base.py           # CommonFrontmatter, EnterpriseFrontmatter
        adr.py            # ADRData + ADRFrontmatter
        decision.py
        incident.py
        postmortem.py
        runbook.py
        architecture.py
        changelog.py
        session.py
        handoff.py
        spec.py
        hu.py
        glossary.py
```

### Contrato principal

```python
from enum import Enum

class DocType(str, Enum):
    SESSION = "session"
    HANDOFF = "handoff"
    SPEC = "spec"
    ADR = "adr"
    DECISION = "decision"
    INCIDENT = "incident"
    POSTMORTEM = "postmortem"
    RUNBOOK = "runbook"
    ARCHITECTURE = "architecture"
    CHANGELOG = "changelog"
    HU = "hu"
    GLOSSARY = "glossary"
```

### Por que es ley

- **Cerrado:** lista finita conocida; cualquier extension requiere ADR.
- **String-valued:** serializable a frontmatter sin transformacion.
- **Single source of truth:** tabla de routing, schemas, writers y retrieval lo importan.
- **Tipado:** mypy garantiza uso correcto en compile time.

### Dataclasses por tipo

Cada `DocType` tiene una dataclass de entrada (data del writer) y un modelo pydantic de frontmatter. Ejemplo:

```python
# cortex/documentation/schemas/adr.py
from dataclasses import dataclass, field

@dataclass
class ADRData:
    title: str
    context: str
    decision: str
    consequences: str
    alternatives_considered: list[str]
    adr_number: int  # asignado por writer si es 0
    supersedes: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    owner: str | None = None
    team: str | None = None
```

---

## CAPA 2: Schema de frontmatter unificado

### Responsabilidad

Garantizar que toda nota tiene metadata estructurada y validable.

### Modelo base (todos los tipos)

```python
# cortex/documentation/schemas/base.py
from pydantic import BaseModel, Field
from datetime import datetime
from cortex.documentation.doc_type import DocType

class CommonFrontmatter(BaseModel):
    schema_version: int = 1
    doc_type: DocType
    title: str
    created_at: datetime
    updated_at: datetime
    tags: list[str] = Field(default_factory=list)
    status: str
    links: list[str] = Field(default_factory=list)
    vault_scope: str = "local"  # "local" | "enterprise"
    fingerprint: str  # sha256 hex
```

### Modelo enterprise (extension)

```python
class AuditEvent(BaseModel):
    actor: str
    action: str
    timestamp: datetime
    reason: str | None = None

class EnterpriseFrontmatter(CommonFrontmatter):
    owner: str  # email
    team: str   # slug
    classification: str = "internal"  # public | internal | confidential
    retention_days: int = 0
    audit_trail: list[AuditEvent] = Field(default_factory=list)
```

### Modelos por tipo

Cada tipo extiende `CommonFrontmatter` con sus campos. Ejemplo ADR:

```python
class ADRFrontmatter(CommonFrontmatter):
    doc_type: DocType = DocType.ADR
    adr_number: int
    supersedes: list[str] = Field(default_factory=list)
    superseded_by: str | None = None
    alternatives_considered: list[str] = Field(default_factory=list)
    acceptance_criteria_met: bool = False
```

### Por que es ley

- **Validacion automatica:** pydantic rechaza notas con campos faltantes o tipos invalidos.
- **schema_version:** futuro-proof; al cambiar el schema, podemos coexistir versiones.
- **fingerprint:** sha256 del contenido. Sirve para sync local<->enterprise sin re-embedding redundante.
- **vault_scope:** una sola estructura, branching condicional para enterprise.

### Validator publico

```python
def validate_frontmatter(yaml_str: str, doc_type: DocType) -> CommonFrontmatter:
    """Validate frontmatter against schema for the given doc_type.

    Raises:
        SchemaValidationError if invalid.
    """
```

---

## CAPA 3: Routing canonico

### Responsabilidad

Mapear `DocType` a todo lo necesario para persistir, indexar y recuperar.

### Modulo

```text
cortex/documentation/routing.py
```

### Contrato

```python
@dataclass(frozen=True)
class RouteSpec:
    doc_type: DocType
    subfolder: str
    filename_template: str        # ej: "ADR-{number:03d}-{slug}.md"
    template_path: Path           # cortex/documentation/templates/adr.md.j2
    writer: Callable               # write_adr_note
    indexer: str = "auto"          # "auto" | "manual"
    promotable: bool = True
    enterprise_subfolder: str | None = None  # "decisions/{project_id}"
    retrieval_boost_per_intent: dict[str, float] = field(default_factory=dict)
    chunking_enabled: bool = True
    chunking_min_words: int = 500
```

### Tabla canonica

```python
DOC_TYPE_ROUTING: dict[DocType, RouteSpec] = {
    DocType.SESSION: RouteSpec(
        doc_type=DocType.SESSION,
        subfolder="sessions",
        filename_template="{date}_{session_id}_{slug}.md",
        template_path=TEMPLATES_DIR / "session.md.j2",
        writer=write_session_note,
        indexer="auto",
        promotable=False,  # SESSION cruda no se promueve; se resume primero
        enterprise_subfolder="sessions/{project_id}",
        retrieval_boost_per_intent={"history": 1.3, "recent": 1.5},
        chunking_enabled=False,  # sessions son cortas
    ),
    DocType.ADR: RouteSpec(
        doc_type=DocType.ADR,
        subfolder="decisions",
        filename_template="ADR-{number:03d}-{slug}.md",
        template_path=TEMPLATES_DIR / "adr.md.j2",
        writer=write_adr_note,
        indexer="auto",
        promotable=True,
        enterprise_subfolder="decisions/{project_id}",
        retrieval_boost_per_intent={"decision": 2.0, "architecture": 1.5},
    ),
    # ... resto en routing-table.md
}
```

### Operaciones publicas

```python
def resolve_route(doc_type: DocType) -> RouteSpec:
    """Get route spec or raise UnknownDocTypeError."""

def render_filename(spec: RouteSpec, context: dict) -> str:
    """Render filename_template with context. Validates required fields."""

def resolve_target_path(
    spec: RouteSpec,
    context: dict,
    vault_root: Path,
    vault_scope: str = "local",
    project_id: str | None = None,
) -> Path:
    """Resolve full target path. Branches on vault_scope."""
```

### Por que es ley

- **Una sola fuente de verdad:** cambia la tabla, cambia el routing globalmente.
- **Codigo declarativo:** la politica de carpetas/naming/templates es data, no logica dispersa.
- **Enterprise como dimension extra:** una columna adicional (`enterprise_subfolder`), no rama del codigo.
- **Documentable:** la tabla se imprime en `cortex docs routing-table` para que el usuario la vea.

---

## CAPA 4: Writers canonicos simetricos

### Responsabilidad

Implementar la secuencia canonica de escritura para cada DocType.

### Modulo

```text
cortex/documentation/
    writers.py            # write_*_note functions
    templates/
        session.md.j2
        handoff.md.j2
        spec.md.j2
        adr.md.j2
        decision.md.j2
        incident.md.j2
        postmortem.md.j2
        runbook.md.j2
        architecture.md.j2
        changelog.md.j2
        hu.md.j2
        glossary.md.j2
```

### Firma simetrica

Cada `write_X_note` sigue exactamente:

```python
def write_X_note(
    data: XData,
    *,
    vault: VaultReader,
    vault_scope: str = "local",
    project_id: str | None = None,
    actor: str | None = None,
) -> Path:
    """Persist X note canonically.

    Steps:
        1. Validate data against schema.
        2. Resolve RouteSpec from DOC_TYPE_ROUTING.
        3. Render template with data.
        4. Compute fingerprint (sha256 of body).
        5. Build frontmatter (CommonFrontmatter or EnterpriseFrontmatter).
        6. Render full markdown (frontmatter + body).
        7. Persist to disk at resolved path.
        8. Index via VaultReader.index_file (incremental).
        9. If enterprise: append audit_trail event with actor.
        10. Return absolute path.

    Raises:
        SchemaValidationError if data invalid.
        DuplicateDocumentError if path already exists and overwrite=False.
    """
```

### Secuencia canonica (todos los writers)

```text
data: XData
   |
   v
[1] validate_against_schema(data, DocType.X)
   |
   v
[2] route = resolve_route(DocType.X)
   |
   v
[3] body = render_template(route.template_path, data)
   |
   v
[4] fingerprint = sha256(body)
   |
   v
[5] frontmatter = build_frontmatter(data, fingerprint, vault_scope)
   |
   v
[6] full_md = frontmatter_yaml + "\n\n" + body
   |
   v
[7] path = resolve_target_path(route, ctx, vault.path, vault_scope, project_id)
   |    path.write_text(full_md)
   v
[8] vault.index_file(rel_path)
   |
   v
[9] if vault_scope == "enterprise":
   |       append_audit_event(path, actor, "created")
   v
return path
```

### Templates (Jinja2)

Ejemplo `adr.md.j2`:

```jinja
# {{ title }}

## Context

{{ context }}

## Decision

{{ decision }}

## Alternatives Considered

{% for alt in alternatives_considered %}
- {{ alt }}
{% endfor %}

## Consequences

{{ consequences }}

{% if supersedes %}
## Supersedes

{% for prev in supersedes %}
- [[{{ prev }}]]
{% endfor %}
{% endif %}
```

### Por que es ley

- **Simetria:** todos los writers se ven igual. Aprendes uno, sabes todos.
- **Validacion al inicio:** falla antes de tocar disco.
- **Index automatico:** sin paso manual; no se olvida.
- **Templates externos:** el ux person puede editar `.md.j2` sin tocar Python.
- **Enterprise diferenciado sin codigo duplicado:** mismo writer, ramita condicional.

---

## CAPA 5: Vectorizacion inteligente

### Responsabilidad

Maximizar la calidad de retrieval modificando como se embedea y donde se cachean los vectores.

### Modulo

```text
cortex/semantic/
    vault_reader.py       # extendido, no reescrito
    chunker.py            # NUEVO
    vector_cache.py       # NUEVO
```

### Sub-capa 5a: Chunking por seccion

**Algoritmo:**

```python
def chunk_document(
    title: str,
    content: str,
    doc_type: DocType,
    tags: list[str],
    *,
    min_words: int = 500,
    boundary: str = "h2",  # "h2" | "h3" | "paragraph"
    overlap_words: int = 0,
) -> list[Chunk]:
    """Split content into chunks for indexing.

    Returns:
        List of Chunk objects. If content has < min_words, returns
        single chunk with full content (no splitting).
    """
```

**Datatype:**

```python
@dataclass(frozen=True)
class Chunk:
    parent_path: str          # ej: "decisions/ADR-007-foo.md"
    chunk_id: str             # ej: "decisions/ADR-007-foo.md#h2-decision"
    section_title: str        # ej: "Decision"
    section_position: int     # 0, 1, 2 ...
    text: str
    doc_type: DocType
    tags: list[str]
    embedding_text: str       # texto efectivo a embedear
```

**Texto efectivo a embedear:**

```text
embedding_text = f"{doc_type.value} {' '.join(tags)} {title} {section_title} {text}"
```

Esto inyecta senal estructural en el vector.

### Sub-capa 5b: Cache en disco

**Layout:**

```text
.cortex/vectors/
    index.json                # {fingerprint: chunk_metadata}
    chunks.bin                # binary array de vectores (384 * float32 * N)
```

**Contrato:**

```python
class VectorCache:
    def get(self, fingerprint: str) -> np.ndarray | None: ...
    def put(self, fingerprint: str, vector: np.ndarray) -> None: ...
    def invalidate(self, fingerprint: str) -> None: ...
    def stats(self) -> CacheStats: ...
```

**Invalidacion:**
- Por `fingerprint` mismatch (contenido cambio).
- Por `schema_version` bump (formato cambio).
- Por mtime del archivo .md mayor que mtime del cache entry.

**Beneficio:**
- 1000 notas con cache valido: <100ms cold start (solo I/O del binario).
- 1000 notas sin cache: ~8s (cada nota se embedea de cero).

### Sub-capa 5c: Sync local <-> enterprise

Cuando una nota se promueve a enterprise:

1. Local conoce `fingerprint`.
2. Enterprise consulta su cache por `fingerprint`.
3. Si hit: reusa el vector sin re-embedear.
4. Si miss: enterprise embedea y cachea bajo el mismo `fingerprint`.

Resuelve el gap S3 del Proposal Enterprise sin reescribir storage.

### Sub-capa 5d: Boost por tipo

Al hacer retrieval, el score final incorpora el `retrieval_boost_per_intent` de la RouteSpec del doc_type del item:

```python
def apply_doc_type_boost(item: EnrichedItem, intent: str) -> float:
    route = resolve_route(item.doc_type)
    boost = route.retrieval_boost_per_intent.get(intent, 1.0)
    return item.enriched_score * boost
```

`intent` lo provee el `QueryIntentDetector` ya existente, extendido con tipos: `decision`, `architecture`, `runbook`, `incident`, `history`, `recent`.

### Por que es ley

- **Chunking resuelve truncacion silenciosa:** notas largas dejan de perder informacion.
- **Cache en disco resuelve cold start:** vaults grandes se cargan instantaneamente.
- **Embedding del frontmatter inyecta senal estructural:** los vectores conocen el tipo.
- **Sync por fingerprint:** evita re-computo entre instancias.

---

## CAPA 6: Recuperacion consciente del schema + telemetria

### Responsabilidad

Hacer que el motor de busqueda razone sobre la estructura, no solo sobre contenido.

### Modulo

```text
cortex/context_enricher/
    enricher.py           # extendido
    filters.py            # NUEVO
    telemetry.py          # NUEVO
    presenter.py          # extendido (agrupacion)
```

### Sub-capa 6a: Filtros estructurales en `WorkContext` y `enrich()`

```python
class EnrichmentFilters(BaseModel):
    doc_types: list[DocType] | None = None
    exclude_doc_types: list[DocType] | None = None
    min_status: str | None = None
    exclude_status: list[str] = Field(default_factory=list)
    tags_required: list[str] = Field(default_factory=list)
    tags_excluded: list[str] = Field(default_factory=list)
    vault_scope: str = "local"  # local | enterprise | all
    max_age_days: int | None = None

def enrich(
    work: WorkContext,
    *,
    filters: EnrichmentFilters | None = None,
    top_k: int | None = None,
) -> EnrichedContext: ...
```

**Aplicacion:**
- Filtros se aplican post-RRF, pre-budget.
- Filtros vacios = sin filtro (default permisivo).

### Sub-capa 6b: Boost por tipo segun intent

Extension del intent detector existente para reconocer:

```python
class QueryIntent(str, Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    DECISION = "decision"          # "por que decidimos X"
    ARCHITECTURE = "architecture"  # "como esta diseniado X"
    RUNBOOK = "runbook"            # "como arranco X"
    INCIDENT = "incident"          # "que paso con X"
    HISTORY = "history"            # "que hicimos sobre X"
    RECENT = "recent"              # "ultimo cambio en X"
```

Mapeo intent -> boost por DocType ya vive en `RouteSpec.retrieval_boost_per_intent`.

### Sub-capa 6c: Presenter agrupado por DocType

```python
class GroupedPresenter:
    def to_markdown(self, ctx: EnrichedContext) -> str:
        groups = self._group_by_doc_type(ctx.items)
        # Renderiza:
        # ## Architecture (2 items)
        #   ...
        # ## ADR (1 item)
        #   ...
```

Reduce ruido cognitivo: el agente recibe items ya organizados por significado.

### Sub-capa 6d: Telemetria in-vault (Mecanismo 1)

En el frontmatter de cada `SESSION` se inyecta:

```yaml
cortex_telemetry:
  enricher_run_id: uuid
  context_items_offered: 8
  context_items_used: 3         # detectado via citas/links en body
  context_hit_rate: 0.375
  context_by_type:
    adr: 1
    runbook: 1
    session: 1
  context_by_strategy:
    topic_search: 2
    entity_search: 1
  context_by_scope:
    local: 3
    enterprise: 0
  enriched_score_p50: 0.42
  enriched_score_p95: 0.71
  enricher_latency_ms: 187
  filters_applied:
    doc_types: ["adr", "runbook"]
    vault_scope: "local"
```

**Captura:**
- `enricher_run_id` se genera al inicio de `enrich()`.
- Items offered/used: `offered` lo sabe el enricher; `used` se infiere post-session leyendo wiki-links del body.
- Hit rate: `used / offered`.

**Agregacion:**
- Comando `cortex memory-report --since 30d` agrega telemetria de todas las sessions.
- Output: distribucion por tipo, estrategia, scope, hit rate global, latencia p50/p95.

### Sub-capa 6e: Observer persistido

Hoy `observer.py` no logguea a disco. Extension:

```python
class PersistentObserver:
    def __init__(self, telemetry_path: Path): ...
    def record_enrichment(self, ctx: EnrichedContext) -> None: ...
    def record_citation(self, run_id: str, source_id: str) -> None: ...
```

Persiste a `.cortex/enrichment-events.jsonl`.

### Por que es ley

- **Filtros estructurales:** el agente puede pedir "solo runbooks", el motor lo entiende.
- **Boost por intent + tipo:** queries de decision retrieven ADR primero, queries de "como arranco" retrieven runbooks primero.
- **Presenter agrupado:** menos ruido en el prompt, mas alineamiento con la mental model del humano.
- **Telemetria in-vault:** cada session es data point; sin esto las decisiones del enricher son ciegas.

---

## Diagramas de flujo

### Flujo: write_adr_note end-to-end

```text
Caller (subagente o test)
   |
   | write_adr_note(ADRData(...), vault=vault, vault_scope="local")
   v
[Capa 4] write_adr_note
   |
   |---> [Capa 2] validate_frontmatter(data, DocType.ADR)
   |       (raises SchemaValidationError si invalido)
   |
   |---> [Capa 3] resolve_route(DocType.ADR)
   |       returns RouteSpec(subfolder="decisions", filename_template="ADR-{number:03d}-{slug}.md", ...)
   |
   |---> render_template("adr.md.j2", data)
   |       returns body markdown
   |
   |---> sha256(body)
   |       returns fingerprint
   |
   |---> build_frontmatter(data, fingerprint, vault_scope="local")
   |       returns YAML
   |
   |---> path = vault_root / "decisions" / "ADR-007-foo.md"
   |       path.write_text(YAML + body)
   |
   |---> [Capa 5] vault.index_file(rel_path)
   |       (puede usar chunking si chunking_enabled=True)
   |
   v
returns path
```

### Flujo: enrich con filtros

```text
WorkContext + EnrichmentFilters(doc_types=[ADR, RUNBOOK])
   |
   v
[Capa 6] ContextEnricher.enrich(work, filters)
   |
   |---> Phase 1: ejecutar 5 strategies (no cambia)
   |
   |---> Phase 2: convertir hits a EnrichedItem (no cambia)
   |
   |---> Phase 2.5: FILTRO ESTRUCTURAL (NUEVO)
   |       items = [i for i in items if i.doc_type in filters.doc_types]
   |
   |---> Phase 3: multi-match boost (no cambia)
   |
   |---> Phase 4: graph/decay/feedback boosts (no cambia)
   |
   |---> Phase 4.5: BOOST POR TIPO + INTENT (NUEVO)
   |       intent = QueryIntentDetector(work.query)
   |       for item: item.score *= route(item.doc_type).boost[intent]
   |
   |---> Phase 5-6: threshold, sort, budget (no cambia)
   |
   |---> Phase 7: TELEMETRIA (NUEVO)
   |       observer.record_enrichment(ctx)
   |
   v
returns EnrichedContext
   |
   v
[Capa 6] GroupedPresenter.to_markdown(ctx)
   |
   v
output agrupado por doc_type
```

### Flujo: indexacion con chunking + cache

```text
vault.index_file("decisions/ADR-007-foo.md")
   |
   v
parse markdown (MarkdownParser)
   |
   v
fingerprint = sha256(content)
   |
   v
chunks = chunker.chunk_document(...) [Capa 5a]
   (1 chunk si content < 500 palabras; N chunks si splitting por H2)
   |
   v
for chunk in chunks:
   chunk_fingerprint = sha256(chunk.embedding_text)
   |
   |---> vector_cache.get(chunk_fingerprint) [Capa 5b]
   |       |
   |       hit -> reuse vector
   |       miss -> embedder.embed(chunk.embedding_text)
   |               vector_cache.put(chunk_fingerprint, vector)
   v
   store {chunk_id: vector} en _embeddings dict
   |
   v
update BM25 stats
   |
   v
persist .cortex_index.json
```

---

## Invariantes de diseno

1. **Capa N solo importa de capas 1..N-1.** Sin imports inversos.
2. **DocType es immutable y conocido en compile time.** Sin lookups dinamicos por string suelto.
3. **Schemas son frozen pydantic models.** Sin mutacion post-construccion.
4. **Routing es declarativo.** Sin codigo procedural condicional sobre DocType.
5. **Writers son puros respecto a side effects esperados.** Mismo input -> mismo output (excepto timestamps y fingerprint que dependen del contenido).
6. **Embeddings son determinsiticos (modulo seed del modelo).** El mismo texto da el mismo vector.
7. **Filtros son aditivos.** Default = sin filtro = comportamiento actual.
8. **Telemetria es no bloqueante.** Si la persistencia falla, log warning, no abortar enrich.
