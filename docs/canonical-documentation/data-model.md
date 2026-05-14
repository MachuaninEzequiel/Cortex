# Data Model - DocType, Dataclasses y Schemas Pydantic

**Documento:** definicion canonica del modelo de datos de documentos
**Audiencia:** implementadores
**Estado:** propuesta de implementacion, modelos consolidados

---

## 1. DocType - Enum cerrado

### Definicion

```python
# cortex/documentation/doc_type.py
from enum import Enum

class DocType(str, Enum):
    """Tipos canonicos de documento en Cortex.

    Lista cerrada. Cualquier extension requiere ADR.

    Inherits from str so the enum is JSON/YAML serializable
    without explicit conversion.
    """
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

### Razon de cada tipo

| DocType | Proposito | Cuando crear |
|---|---|---|
| `SESSION` | Cierre de trabajo: que se hizo, que falta, decisiones in-flight | Al terminar una sesion de trabajo |
| `HANDOFF` | Entrega de trabajo abierto a la proxima sesion | Cuando una sesion no completa cierra; estado != "completed" |
| `SPEC` | Especificacion de algo a implementar | Antes de empezar trabajo grande |
| `ADR` | Decision arquitectural con criterios Tripartita | Hard-to-reverse + Surprising + Trade-off |
| `DECISION` | Decision con razon documentada pero no arquitectural | Cuando hay alternativa rechazada pero no es ADR |
| `INCIDENT` | Reporte de incidente operativo | Ante caida, bug critico, comportamiento inesperado |
| `POSTMORTEM` | Analisis post-incidente con root cause | Despues de resolver incidente, especialmente severity >= medium |
| `RUNBOOK` | Procedimiento operativo paso a paso | Para operaciones repetibles (deploy, rollback, incident response) |
| `ARCHITECTURE` | Descripcion de diseno de un componente o sistema | Cuando un componente merece documentacion permanente |
| `CHANGELOG` | Entrada de cambios por release | Por cada release versionado |
| `HU` | Historia de usuario / work item externo | Cuando se sincroniza con sistema externo (Jira, Linear, etc) |
| `GLOSSARY` | Termino del ubiquitous language | Cada vez que se acuna o redefine un termino |

### Helpers

```python
def doc_type_from_str(value: str) -> DocType:
    """Parse string to DocType. Raises UnknownDocTypeError."""

def doc_type_from_path(path: Path) -> DocType | None:
    """Infer doc_type from path. Returns None if cannot infer.

    Used by backfill (Fase 11) to migrate notes without explicit doc_type.
    """

def all_doc_types() -> list[DocType]:
    """Return all valid DocType values."""

def promotable_doc_types() -> list[DocType]:
    """Return doc_types that can be promoted to enterprise."""
```

---

## 2. Dataclasses de entrada (data del writer)

Cada `write_X_note` recibe una dataclass tipada. Estas son inputs, no schemas de frontmatter (los schemas viven en pydantic). Razon: dataclasses son mas livianas para construccion incremental por el caller.

### Common

```python
# cortex/documentation/data.py
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class CommonWriteData:
    """Campos comunes a todos los writers."""
    title: str
    tags: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    status: str = ""
    owner: str | None = None
    team: str | None = None
    classification: str | None = None
    retention_days: int | None = None
```

### SessionData

```python
@dataclass
class SessionData(CommonWriteData):
    session_id: str = ""
    spec_summary: str = ""
    changes_made: list[str] = field(default_factory=list)
    files_touched: list[str] = field(default_factory=list)
    key_decisions: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    pr: str | None = None
    branch: str | None = None
    commit: str | None = None
    verified_state: list[str] = field(default_factory=list)
    unverified_claims: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    suggested_skills: list[str] = field(default_factory=list)
    cortex_telemetry: dict | None = None
```

### HandoffData

```python
@dataclass
class HandoffData(CommonWriteData):
    parent_session_id: str = ""
    next_session_needs: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    verified_state: list[str] = field(default_factory=list)
    unverified_claims: list[str] = field(default_factory=list)
    suggested_skills: list[str] = field(default_factory=list)
    context_required: str = ""
```

### SpecData

```python
@dataclass
class SpecData(CommonWriteData):
    goal: str = ""
    requirements: list[str] = field(default_factory=list)
    files_in_scope: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
```

### ADRData

```python
@dataclass
class ADRData(CommonWriteData):
    context: str = ""
    decision: str = ""
    alternatives_considered: list[str] = field(default_factory=list)
    consequences: str = ""
    adr_number: int = 0  # 0 = auto-asignar al siguiente
    supersedes: list[str] = field(default_factory=list)
    superseded_by: str | None = None
    acceptance_criteria_met: bool = False
```

### DecisionData

```python
@dataclass
class DecisionData(CommonWriteData):
    context: str = ""
    decision: str = ""
    alternative_rejected: str = ""
    reason: str = ""
    reversible_within_days: int = 0
```

### IncidentData

```python
@dataclass
class IncidentData(CommonWriteData):
    incident_number: int = 0  # 0 = auto-asignar
    severity: str = "medium"  # low | medium | high | critical
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    affected_services: list[str] = field(default_factory=list)
    timeline: list[str] = field(default_factory=list)
    impact: str = ""
    short_description: str = ""
    root_cause_postmortem: str | None = None  # path al postmortem
```

### PostmortemData

```python
@dataclass
class PostmortemData(CommonWriteData):
    incident_number: int = 0
    incident_path: str = ""
    root_cause: str = ""
    contributing_factors: list[str] = field(default_factory=list)
    what_went_well: list[str] = field(default_factory=list)
    what_went_wrong: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    timeline: list[str] = field(default_factory=list)
    severity: str = "medium"
```

### RunbookData

```python
@dataclass
class RunbookData(CommonWriteData):
    runbook_kind: str = "operational"  # deploy | rollback | incident-response | data-migration | operational
    description: str = ""
    prerequisites: list[str] = field(default_factory=list)
    procedure: list[str] = field(default_factory=list)
    rollback_procedure: list[str] = field(default_factory=list)
    verification: list[str] = field(default_factory=list)
    applies_to: list[str] = field(default_factory=list)
    estimated_duration_minutes: int = 0
    last_verified_at: datetime | None = None
```

### ArchitectureData

```python
@dataclass
class ArchitectureData(CommonWriteData):
    summary: str = ""
    components: list[str] = field(default_factory=list)
    diagrams: list[str] = field(default_factory=list)  # paths a imagenes/asciidoc
    contracts: list[str] = field(default_factory=list)
    rationale: str = ""
    related_adrs: list[str] = field(default_factory=list)
```

### ChangelogData

```python
@dataclass
class ChangelogData(CommonWriteData):
    version: str = ""  # ej: "v1.2.3"
    release_date: datetime | None = None
    added: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    deprecated: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    fixed: list[str] = field(default_factory=list)
    security: list[str] = field(default_factory=list)
```

### HUData

```python
@dataclass
class HUData(CommonWriteData):
    external_id: str = ""
    source: str = ""  # "jira" | "linear" | "github" | etc
    kind: str = "story"  # story | task | bug | epic
    description: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)
    assignee: str | None = None
    external_url: str | None = None
    synced_at: datetime | None = None
```

### GlossaryEntryData

```python
@dataclass
class GlossaryEntryData(CommonWriteData):
    term: str = ""
    definition: str = ""
    examples: list[str] = field(default_factory=list)
    related_terms: list[str] = field(default_factory=list)
    domain: str | None = None  # "auth", "billing", etc
```

---

## 3. Schemas pydantic de frontmatter

Mientras las dataclasses son inputs, los schemas pydantic son lo que vive en el frontmatter persistido. Hay overlap pero NO son lo mismo: el schema agrega campos derivados (`fingerprint`, `schema_version`, `updated_at`).

### CommonFrontmatter

```python
# cortex/documentation/schemas/base.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from cortex.documentation.doc_type import DocType

class CommonFrontmatter(BaseModel):
    model_config = ConfigDict(frozen=True, validate_assignment=True)

    schema_version: int = 1
    doc_type: DocType
    title: str
    created_at: datetime
    updated_at: datetime
    tags: list[str] = Field(default_factory=list)
    status: str
    links: list[str] = Field(default_factory=list)
    vault_scope: str = "local"  # "local" | "enterprise"
    fingerprint: str  # sha256 hex of body content
```

### EnterpriseFrontmatter

```python
class AuditEvent(BaseModel):
    actor: str
    action: str  # "created" | "updated" | "promoted" | "reviewed" | "rejected"
    timestamp: datetime
    reason: str | None = None

class EnterpriseFrontmatter(CommonFrontmatter):
    owner: str  # email
    team: str   # slug
    classification: str = "internal"  # public | internal | confidential
    retention_days: int = 0  # 0 = sin retencion
    audit_trail: list[AuditEvent] = Field(default_factory=list)
```

### Schemas por tipo

```python
# cortex/documentation/schemas/session.py
class CortexTelemetry(BaseModel):
    enricher_run_id: str
    context_items_offered: int
    context_items_used: int
    context_hit_rate: float
    context_by_type: dict[str, int]
    context_by_strategy: dict[str, int]
    context_by_scope: dict[str, int]
    enriched_score_p50: float
    enriched_score_p95: float
    enricher_latency_ms: int
    filters_applied: dict

class SessionFrontmatter(CommonFrontmatter):
    doc_type: DocType = DocType.SESSION
    session_id: str
    pr: str | None = None
    branch: str | None = None
    commit: str | None = None
    cortex_telemetry: CortexTelemetry | None = None

# cortex/documentation/schemas/adr.py
class ADRFrontmatter(CommonFrontmatter):
    doc_type: DocType = DocType.ADR
    adr_number: int
    supersedes: list[str] = Field(default_factory=list)
    superseded_by: str | None = None
    alternatives_considered: list[str] = Field(default_factory=list)
    acceptance_criteria_met: bool = False

# cortex/documentation/schemas/incident.py
class IncidentFrontmatter(CommonFrontmatter):
    doc_type: DocType = DocType.INCIDENT
    incident_number: int
    severity: str  # low | medium | high | critical
    opened_at: datetime
    closed_at: datetime | None = None
    affected_services: list[str] = Field(default_factory=list)
    root_cause_postmortem: str | None = None

# cortex/documentation/schemas/postmortem.py
class PostmortemFrontmatter(CommonFrontmatter):
    doc_type: DocType = DocType.POSTMORTEM
    incident_number: int
    incident_path: str
    severity: str

# cortex/documentation/schemas/runbook.py
class RunbookFrontmatter(CommonFrontmatter):
    doc_type: DocType = DocType.RUNBOOK
    runbook_kind: str  # deploy | rollback | incident-response | data-migration | operational
    applies_to: list[str] = Field(default_factory=list)
    estimated_duration_minutes: int = 0
    last_verified_at: datetime | None = None

# ... resto en cada modulo
```

### Discriminated union

Para validacion polimorfica al cargar frontmatter:

```python
# cortex/documentation/schemas/__init__.py
from typing import Annotated, Union
from pydantic import Field

FrontmatterUnion = Annotated[
    Union[
        SessionFrontmatter,
        HandoffFrontmatter,
        SpecFrontmatter,
        ADRFrontmatter,
        DecisionFrontmatter,
        IncidentFrontmatter,
        PostmortemFrontmatter,
        RunbookFrontmatter,
        ArchitectureFrontmatter,
        ChangelogFrontmatter,
        HUFrontmatter,
        GlossaryFrontmatter,
    ],
    Field(discriminator="doc_type"),
]
```

### Validador publico

```python
# cortex/documentation/validation.py
def validate_frontmatter(yaml_str: str) -> CommonFrontmatter:
    """Parse YAML frontmatter and validate against schema.

    Returns the correct subclass based on doc_type field.

    Raises:
        SchemaValidationError if invalid or doc_type missing.
    """
    import yaml
    raw = yaml.safe_load(yaml_str)
    if "doc_type" not in raw:
        raise SchemaValidationError("doc_type field is required")
    return _validate_by_type(raw)

def _validate_by_type(raw: dict) -> CommonFrontmatter:
    doc_type = DocType(raw["doc_type"])
    schema_class = SCHEMA_BY_TYPE[doc_type]
    if raw.get("vault_scope") == "enterprise":
        schema_class = SCHEMA_BY_TYPE_ENTERPRISE[doc_type]
    return schema_class.model_validate(raw)
```

---

## 4. Status validos por tipo

Cada tipo tiene un set valido de `status`. Validador rechaza si no esta en la lista.

```python
VALID_STATUSES: dict[DocType, frozenset[str]] = {
    DocType.SESSION: frozenset({
        "draft", "completed", "handoff", "fallback", "auto-draft",
    }),
    DocType.HANDOFF: frozenset({"open", "consumed", "stale"}),
    DocType.SPEC: frozenset({"draft", "approved", "implementing", "done", "abandoned"}),
    DocType.ADR: frozenset({"proposed", "accepted", "superseded", "rejected"}),
    DocType.DECISION: frozenset({"active", "reverted"}),
    DocType.INCIDENT: frozenset({"open", "mitigated", "closed"}),
    DocType.POSTMORTEM: frozenset({"draft", "published", "actions-tracked", "complete"}),
    DocType.RUNBOOK: frozenset({"draft", "verified", "deprecated"}),
    DocType.ARCHITECTURE: frozenset({"draft", "current", "deprecated"}),
    DocType.CHANGELOG: frozenset({"unreleased", "released"}),
    DocType.HU: frozenset({"backlog", "in-progress", "done", "cancelled"}),
    DocType.GLOSSARY: frozenset({"draft", "canonical", "deprecated"}),
}
```

---

## 5. Errors

```python
# cortex/documentation/errors.py
class DocumentationError(Exception):
    """Base error."""

class SchemaValidationError(DocumentationError):
    """Frontmatter does not validate."""

class UnknownDocTypeError(DocumentationError):
    """doc_type is not a valid DocType."""

class RoutingError(DocumentationError):
    """RouteSpec resolution failed."""

class DuplicateDocumentError(DocumentationError):
    """Document already exists at target path and overwrite=False."""

class TemplateRenderError(DocumentationError):
    """Jinja2 template render failed."""
```

---

## 6. Tabla de uso por capa

| Modulo | Importa de | Usa para |
|---|---|---|
| `cortex/documentation/doc_type.py` | nada | Enum DocType |
| `cortex/documentation/data.py` | `doc_type` | Dataclasses de entrada |
| `cortex/documentation/schemas/*` | `doc_type` | Frontmatter validation |
| `cortex/documentation/routing.py` | `doc_type` | RouteSpec table |
| `cortex/documentation/writers.py` | `data, schemas, routing` | Write functions |
| `cortex/documentation/validation.py` | `schemas` | Validate any frontmatter |
| `cortex/context_enricher/*` | `doc_type, schemas` | Filters, boost, presenter |
| `cortex/semantic/vault_reader.py` | `doc_type, schemas` | index_file con metadata |
| `cortex/enterprise/*` | `data, schemas, routing` | Promotion DocType-aware |

---

## 7. Convenciones de tipado

1. **Todo es immutable cuando puede:** dataclasses con `frozen=True` donde aplique; pydantic con `model_config = ConfigDict(frozen=True)`.
2. **Listas vacias en vez de None:** `tags: list[str] = field(default_factory=list)` no `tags: list[str] | None = None`.
3. **datetime con timezone:** `datetime.now(UTC)` no `datetime.now()`.
4. **Strings nunca son None si tienen default:** `title: str = ""` no `title: str | None = None`.
5. **Enum string-valued:** `class X(str, Enum)` para serializacion JSON/YAML directa.

---

## 8. Migracion de modelos legacy

Los modelos actuales (`SemanticDocument`, `EpisodicMemoryEntry`, etc) se mantienen para no romper memoria episodica y motor de busqueda. Solo agregamos:

- `EnrichedItem.doc_type: DocType | None` (default None para legacy).
- `EnrichedItem.status: str | None` (default None).
- `EnrichedItem.vault_scope: str = "local"`.
- `SemanticDocument.frontmatter: dict | None` (raw YAML para post-procesamiento).

Esto se hace en Fase 01 para no romper retrieval existente.
