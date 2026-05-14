# Routing Table - DOC_TYPE_ROUTING Canonica

**Documento:** especificacion completa de la tabla de routing
**Audiencia:** implementadores
**Estado:** especificacion normativa

---

## 1. Contrato `RouteSpec`

```python
# cortex/documentation/routing.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from cortex.documentation.doc_type import DocType

@dataclass(frozen=True)
class RouteSpec:
    """Routing specification for a DocType."""

    doc_type: DocType

    # Storage
    subfolder: str                         # ej: "decisions"
    filename_template: str                 # ej: "ADR-{number:03d}-{slug}.md"

    # Rendering
    template_path: Path                    # ruta al .md.j2

    # Writing
    writer: Callable                       # ej: write_adr_note
    indexer: str = "auto"                  # "auto" | "manual"

    # Enterprise
    promotable: bool = False
    promotion_mode: str = "as-is"          # "as-is" | "summarize" | "review-required"
    enterprise_subfolder: str | None = None  # con `{project_id}` placeholder

    # Retrieval
    retrieval_boost_per_intent: dict[str, float] = field(default_factory=dict)
    chunking_enabled: bool = True
    chunking_min_words: int = 500
    chunking_boundary: str = "h2"           # "h2" | "h3" | "paragraph"

    # Webgraph
    webgraph_color: str = "gray"            # hex o nombre css
    webgraph_shape: str = "rectangle"        # rectangle | ellipse | diamond | hexagon

    # Lifecycle
    requires_review_before_publish: bool = False
    auto_expire_days: int = 0                # 0 = nunca expira
```

---

## 2. Templates dir

```python
TEMPLATES_DIR = Path(__file__).parent / "templates"
# resuelve a cortex/documentation/templates/
```

---

## 3. Tabla canonica

```python
from cortex.documentation.writers import (
    write_session_note, write_handoff_note, write_spec_note,
    write_adr_note, write_decision_note, write_incident_note,
    write_postmortem_note, write_runbook_note, write_architecture_note,
    write_changelog_note, write_hu_note, write_glossary_entry,
)

DOC_TYPE_ROUTING: dict[DocType, RouteSpec] = {

    DocType.SESSION: RouteSpec(
        doc_type=DocType.SESSION,
        subfolder="sessions",
        filename_template="{date}_{session_id}_{slug}.md",
        template_path=TEMPLATES_DIR / "session.md.j2",
        writer=write_session_note,
        indexer="auto",
        promotable=True,
        promotion_mode="summarize",   # se promueve como resumen, no raw
        enterprise_subfolder="sessions/{project_id}",
        retrieval_boost_per_intent={
            "history": 1.3,
            "recent": 1.5,
            "episodic": 1.4,
        },
        chunking_enabled=False,        # sessions son cortas
        webgraph_color="#88aaff",
        webgraph_shape="rectangle",
    ),

    DocType.HANDOFF: RouteSpec(
        doc_type=DocType.HANDOFF,
        subfolder="handoffs",
        filename_template="{date}_{slug}.md",
        template_path=TEMPLATES_DIR / "handoff.md.j2",
        writer=write_handoff_note,
        indexer="auto",
        promotable=False,
        enterprise_subfolder=None,
        retrieval_boost_per_intent={
            "recent": 2.0,             # handoffs recientes son criticos
            "history": 1.0,
        },
        chunking_enabled=False,
        webgraph_color="#ffaa44",
        webgraph_shape="diamond",
        auto_expire_days=14,          # handoff stale despues de 14 dias
    ),

    DocType.SPEC: RouteSpec(
        doc_type=DocType.SPEC,
        subfolder="specs",
        filename_template="{date}_{slug}.md",
        template_path=TEMPLATES_DIR / "spec.md.j2",
        writer=write_spec_note,
        indexer="auto",
        promotable=True,
        promotion_mode="as-is",
        enterprise_subfolder="specs/{project_id}",
        retrieval_boost_per_intent={
            "spec": 2.0,
            "requirements": 1.8,
            "implementation": 1.4,
        },
        chunking_enabled=True,
        chunking_min_words=500,
        webgraph_color="#88ddaa",
        webgraph_shape="rectangle",
    ),

    DocType.ADR: RouteSpec(
        doc_type=DocType.ADR,
        subfolder="decisions",
        filename_template="ADR-{number:03d}-{slug}.md",
        template_path=TEMPLATES_DIR / "adr.md.j2",
        writer=write_adr_note,
        indexer="auto",
        promotable=True,
        promotion_mode="as-is",
        enterprise_subfolder="decisions/{project_id}",
        retrieval_boost_per_intent={
            "decision": 2.0,
            "architecture": 1.5,
            "history": 1.2,
            "rationale": 1.8,
        },
        chunking_enabled=True,
        chunking_min_words=400,
        chunking_boundary="h2",
        webgraph_color="#cc66ff",
        webgraph_shape="hexagon",
        requires_review_before_publish=False,   # ADRs pueden ser proposed
    ),

    DocType.DECISION: RouteSpec(
        doc_type=DocType.DECISION,
        subfolder="decisions",
        filename_template="DEC-{date}-{slug}.md",
        template_path=TEMPLATES_DIR / "decision.md.j2",
        writer=write_decision_note,
        indexer="auto",
        promotable=True,
        promotion_mode="as-is",
        enterprise_subfolder="decisions/{project_id}",
        retrieval_boost_per_intent={
            "decision": 1.5,
            "history": 1.2,
        },
        chunking_enabled=False,
        webgraph_color="#aa88cc",
        webgraph_shape="hexagon",
    ),

    DocType.INCIDENT: RouteSpec(
        doc_type=DocType.INCIDENT,
        subfolder="incidents",
        filename_template="INC-{number:03d}-{date}-{slug}.md",
        template_path=TEMPLATES_DIR / "incident.md.j2",
        writer=write_incident_note,
        indexer="auto",
        promotable=True,
        promotion_mode="as-is",         # promote if severity >= medium
        enterprise_subfolder="incidents/{project_id}",
        retrieval_boost_per_intent={
            "incident": 2.5,
            "recent": 2.0,
            "history": 1.5,
            "runbook": 1.3,             # runbook search relevante a incidents
        },
        chunking_enabled=True,
        chunking_min_words=500,
        webgraph_color="#ff6666",
        webgraph_shape="diamond",
    ),

    DocType.POSTMORTEM: RouteSpec(
        doc_type=DocType.POSTMORTEM,
        subfolder="postmortems",
        filename_template="PM-{incident_number:03d}-{slug}.md",
        template_path=TEMPLATES_DIR / "postmortem.md.j2",
        writer=write_postmortem_note,
        indexer="auto",
        promotable=True,
        promotion_mode="as-is",         # postmortems siempre se promueven
        enterprise_subfolder="postmortems/{project_id}",
        retrieval_boost_per_intent={
            "postmortem": 2.5,
            "incident": 2.0,
            "root-cause": 2.2,
            "history": 1.5,
        },
        chunking_enabled=True,
        chunking_min_words=500,
        webgraph_color="#aa4444",
        webgraph_shape="diamond",
        requires_review_before_publish=True,   # postmortems requieren review
    ),

    DocType.RUNBOOK: RouteSpec(
        doc_type=DocType.RUNBOOK,
        subfolder="runbooks",
        filename_template="RB-{slug}.md",
        template_path=TEMPLATES_DIR / "runbook.md.j2",
        writer=write_runbook_note,
        indexer="auto",
        promotable=True,
        promotion_mode="review-required",
        enterprise_subfolder="runbooks/{project_id}",
        retrieval_boost_per_intent={
            "runbook": 2.5,
            "procedure": 2.0,
            "deploy": 1.8,
            "rollback": 1.8,
            "operations": 1.5,
        },
        chunking_enabled=True,
        chunking_min_words=400,
        chunking_boundary="h2",
        webgraph_color="#66cccc",
        webgraph_shape="rectangle",
        requires_review_before_publish=True,
        auto_expire_days=180,           # runbooks deben re-verificarse cada 6 meses
    ),

    DocType.ARCHITECTURE: RouteSpec(
        doc_type=DocType.ARCHITECTURE,
        subfolder="architecture",
        filename_template="{slug}.md",
        template_path=TEMPLATES_DIR / "architecture.md.j2",
        writer=write_architecture_note,
        indexer="auto",
        promotable=True,
        promotion_mode="as-is",
        enterprise_subfolder="architecture/{project_id}",
        retrieval_boost_per_intent={
            "architecture": 2.5,
            "design": 2.0,
            "decision": 1.5,
            "overview": 1.5,
        },
        chunking_enabled=True,
        chunking_min_words=500,
        chunking_boundary="h2",
        webgraph_color="#6688cc",
        webgraph_shape="rectangle",
    ),

    DocType.CHANGELOG: RouteSpec(
        doc_type=DocType.CHANGELOG,
        subfolder="changelog",
        filename_template="{version}.md",
        template_path=TEMPLATES_DIR / "changelog.md.j2",
        writer=write_changelog_note,
        indexer="auto",
        promotable=True,
        promotion_mode="as-is",
        enterprise_subfolder="changelog/{project_id}",
        retrieval_boost_per_intent={
            "changelog": 1.5,
            "release": 1.5,
            "version": 1.5,
        },
        chunking_enabled=True,
        chunking_min_words=500,
        webgraph_color="#999999",
        webgraph_shape="rectangle",
    ),

    DocType.HU: RouteSpec(
        doc_type=DocType.HU,
        subfolder="hu",
        filename_template="HU-{external_id}.md",
        template_path=TEMPLATES_DIR / "hu.md.j2",
        writer=write_hu_note,
        indexer="auto",
        promotable=False,            # HUs son work items, no conocimiento
        enterprise_subfolder=None,
        retrieval_boost_per_intent={
            "task": 1.3,
            "requirements": 1.4,
            "current-work": 1.5,
        },
        chunking_enabled=False,
        webgraph_color="#ccaa66",
        webgraph_shape="ellipse",
    ),

    DocType.GLOSSARY: RouteSpec(
        doc_type=DocType.GLOSSARY,
        subfolder="glossary",
        filename_template="{term-slug}.md",
        template_path=TEMPLATES_DIR / "glossary.md.j2",
        writer=write_glossary_entry,
        indexer="auto",
        promotable=True,
        promotion_mode="as-is",
        enterprise_subfolder="glossary",   # glossary es global, sin namespacing
        retrieval_boost_per_intent={
            "glossary": 2.0,
            "definition": 2.5,
            "term": 2.5,
        },
        chunking_enabled=False,
        webgraph_color="#cccc66",
        webgraph_shape="ellipse",
    ),

}
```

---

## 4. Operaciones publicas

```python
# cortex/documentation/routing.py

class UnknownDocTypeError(DocumentationError): ...
class RoutingError(DocumentationError): ...

def resolve_route(doc_type: DocType) -> RouteSpec:
    """Get route spec for the given doc_type.

    Raises:
        UnknownDocTypeError if doc_type not in DOC_TYPE_ROUTING.
    """
    if doc_type not in DOC_TYPE_ROUTING:
        raise UnknownDocTypeError(f"{doc_type} not in routing table")
    return DOC_TYPE_ROUTING[doc_type]


def render_filename(spec: RouteSpec, context: dict) -> str:
    """Render filename_template with context.

    Context must include all placeholders required by the template.
    For example, for ADR: {number, slug}.

    Raises:
        RoutingError if a required placeholder is missing.
    """


def resolve_target_path(
    spec: RouteSpec,
    context: dict,
    vault_root: Path,
    vault_scope: str = "local",
    project_id: str | None = None,
) -> Path:
    """Resolve full target path inside vault.

    For vault_scope='local': vault_root / spec.subfolder / filename
    For vault_scope='enterprise': vault_root / spec.enterprise_subfolder.format(project_id=...) / filename

    Raises:
        RoutingError if enterprise scope without project_id, or no enterprise_subfolder
        defined for this DocType.
    """


def list_all_routes() -> list[RouteSpec]:
    """Return all RouteSpecs in DOC_TYPE_ROUTING. Used by cortex docs routing-table CLI."""


def routes_by_subfolder() -> dict[str, RouteSpec]:
    """Inverse map: subfolder -> RouteSpec. Used by webgraph and backfill."""
```

---

## 5. CLI

Comando para inspeccionar la tabla:

```bash
$ cortex docs routing-table
| DocType       | Subfolder      | Filename pattern                    | Writer                  | Indexer | Promotable |
|---------------|----------------|-------------------------------------|-------------------------|---------|------------|
| session       | sessions       | {date}_{session_id}_{slug}.md       | write_session_note      | auto    | summarize  |
| handoff       | handoffs       | {date}_{slug}.md                    | write_handoff_note      | auto    | no         |
| spec          | specs          | {date}_{slug}.md                    | write_spec_note         | auto    | as-is      |
| adr           | decisions      | ADR-{number:03d}-{slug}.md          | write_adr_note          | auto    | as-is      |
| ...           | ...            | ...                                 | ...                     | ...     | ...        |
```

```bash
$ cortex docs routing-table --doc-type adr --json
{
  "doc_type": "adr",
  "subfolder": "decisions",
  "filename_template": "ADR-{number:03d}-{slug}.md",
  "template_path": "cortex/documentation/templates/adr.md.j2",
  "writer": "write_adr_note",
  "indexer": "auto",
  "promotable": true,
  "promotion_mode": "as-is",
  "enterprise_subfolder": "decisions/{project_id}",
  "retrieval_boost_per_intent": {
    "decision": 2.0,
    "architecture": 1.5,
    "history": 1.2,
    "rationale": 1.8
  },
  "chunking_enabled": true,
  "chunking_min_words": 400,
  "chunking_boundary": "h2",
  "webgraph_color": "#cc66ff",
  "webgraph_shape": "hexagon",
  "requires_review_before_publish": false
}
```

---

## 6. Casos especiales

### 6.1 ADR y DECISION comparten `subfolder`

Razon: ambos son decisiones; ADR es subset (criterios Tripartita). Coexisten en `decisions/` con prefijos distintos:
- ADR: `ADR-007-foo.md`
- DECISION: `DEC-2026-05-14-foo.md`

Webgraph los distingue por `doc_type` aunque vivan en la misma carpeta.

### 6.2 GLOSSARY no se namespaces en enterprise

Razon: terminos del ubiquitous language deben ser globales en una organizacion. Sin `{project_id}`.

### 6.3 HU no es promotable

Razon: las HUs son work items operativos, no conocimiento. No tienen sentido en vault enterprise como referencia.

### 6.4 HANDOFF auto-expira

Razon: handoff stale es ruido. Tras 14 dias sin consumir, status = `stale` automaticamente (cron en `cortex docs maintenance`).

### 6.5 RUNBOOK auto-expira

Razon: runbooks no verificados son peligrosos. Tras 180 dias sin `last_verified_at`, warning en `cortex docs validate`.

---

## 7. Invariantes

1. **Todos los `DocType` deben tener una entrada en `DOC_TYPE_ROUTING`.** Test estatico verifica.
2. **Cada `template_path` debe existir.** Test estatico verifica.
3. **Cada `writer` debe ser callable importable.** Test estatico verifica.
4. **`enterprise_subfolder` con `{project_id}` requiere `project_id` al resolve.** Falla loud si missing.
5. **`promotion_mode: 'review-required'` implica `requires_review_before_publish: True`.** Sanity check.

---

## 8. Extension futura

Para agregar un nuevo `DocType`:

1. ADR justifica el tipo.
2. Agregar al `DocType` enum.
3. Crear dataclass + schema pydantic.
4. Crear template `.md.j2`.
5. Implementar `write_X_note`.
6. Agregar `RouteSpec` en `DOC_TYPE_ROUTING`.
7. Agregar `VALID_STATUSES[DocType.X]`.
8. Agregar boost por intent si aplica.
9. Tests unitarios.
10. Documentar en `routing-table.md` y `frontmatter-schema.md`.

No se permite agregar `DocType` sin completar los 10 pasos.
