# Fase 01 - DocType y Schema

**Fuente:** `docs/canonical-documentation/README.md`
**Estado:** Completada (2026-05-14) - ver [`REALIZACION.md`](REALIZACION.md)
**Esfuerzo estimado:** 1.5 dias (real: ~2 horas)
**Riesgo:** bajo
**Dependencias:** Fase 00

---

## 1. Objetivo

Implementar la **Capa 1 (DocType)** y la **Capa 2 (Schema de frontmatter)** completas:
- Enum `DocType` cerrado con 12 valores.
- 12 dataclasses de entrada (uno por tipo).
- 12 modelos pydantic de frontmatter (uno por tipo).
- `EnterpriseFrontmatter` extension.
- Validador publico con discriminated union.
- Tabla `VALID_STATUSES`.

---

## 2. Archivos a crear

```text
cortex/documentation/
    doc_type.py                     # Enum DocType + helpers
    data.py                          # Dataclasses XData
    validation.py                    # Validator publico
    schemas/
        __init__.py                  # Re-export + SCHEMA_BY_TYPE map
        base.py                      # CommonFrontmatter, EnterpriseFrontmatter, AuditEvent
        session.py
        handoff.py
        spec.py
        adr.py
        decision.py
        incident.py
        postmortem.py
        runbook.py
        architecture.py
        changelog.py
        hu.py
        glossary.py

tests/unit/documentation/
    test_doc_type.py
    test_schema_base.py
    test_schema_session.py
    test_schema_handoff.py
    test_schema_spec.py
    test_schema_adr.py
    test_schema_decision.py
    test_schema_incident.py
    test_schema_postmortem.py
    test_schema_runbook.py
    test_schema_architecture.py
    test_schema_changelog.py
    test_schema_hu.py
    test_schema_glossary.py
    test_validation.py
```

---

## 3. Responsabilidades por archivo

### `doc_type.py`

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


def doc_type_from_str(value: str) -> DocType: ...
def doc_type_from_path(path: Path) -> DocType | None: ...
def all_doc_types() -> list[DocType]: ...
def promotable_doc_types() -> list[DocType]: ...

VALID_STATUSES: dict[DocType, frozenset[str]] = {
    DocType.SESSION: frozenset({"draft", "completed", "handoff", "fallback", "auto-draft"}),
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

### `data.py`

12 dataclasses + `CommonWriteData` base. Detalle completo en `data-model.md` seccion 2.

### `schemas/base.py`

```python
from pydantic import BaseModel, Field, ConfigDict, model_validator
from datetime import datetime
from cortex.documentation.doc_type import DocType, VALID_STATUSES

class CommonFrontmatter(BaseModel):
    model_config = ConfigDict(frozen=True, validate_assignment=True)

    schema_version: int = 1
    doc_type: DocType
    title: str = Field(min_length=1)
    created_at: datetime
    updated_at: datetime
    tags: list[str] = Field(default_factory=list)
    status: str
    links: list[str] = Field(default_factory=list)
    vault_scope: str = "local"
    fingerprint: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_dates(self):
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must be >= created_at")
        return self

    @model_validator(mode="after")
    def validate_status(self):
        valid = VALID_STATUSES.get(self.doc_type)
        if valid is not None and self.status not in valid:
            raise ValueError(f"status '{self.status}' invalid for doc_type '{self.doc_type}'. Valid: {valid}")
        return self

    @model_validator(mode="after")
    def validate_vault_scope(self):
        if self.vault_scope not in {"local", "enterprise"}:
            raise ValueError(f"vault_scope must be 'local' or 'enterprise', got '{self.vault_scope}'")
        return self


class AuditEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    actor: str
    action: str
    timestamp: datetime
    reason: str | None = None


class EnterpriseFrontmatter(CommonFrontmatter):
    owner: str = Field(pattern=r"^[\w.+-]+@[\w-]+\.[\w.-]+$")  # email
    team: str = Field(pattern=r"^[a-z0-9-]+$")
    classification: str = "internal"
    retention_days: int = Field(default=0, ge=0)
    audit_trail: list[AuditEvent] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_classification(self):
        if self.classification not in {"public", "internal", "confidential"}:
            raise ValueError("classification must be public, internal, or confidential")
        return self

    @model_validator(mode="after")
    def validate_enterprise_scope(self):
        if self.vault_scope != "enterprise":
            raise ValueError("EnterpriseFrontmatter requires vault_scope='enterprise'")
        return self
```

### `schemas/<type>.py`

Uno por tipo. Cada uno extiende `CommonFrontmatter` con campos especificos. Ejemplo `adr.py`:

```python
from pydantic import Field
from cortex.documentation.doc_type import DocType
from cortex.documentation.schemas.base import CommonFrontmatter, EnterpriseFrontmatter


class ADRFrontmatter(CommonFrontmatter):
    doc_type: DocType = DocType.ADR
    adr_number: int = Field(ge=1)
    supersedes: list[str] = Field(default_factory=list)
    superseded_by: str | None = None
    alternatives_considered: list[str] = Field(default_factory=list)
    acceptance_criteria_met: bool = False


class ADRFrontmatterEnterprise(EnterpriseFrontmatter):
    doc_type: DocType = DocType.ADR
    adr_number: int = Field(ge=1)
    supersedes: list[str] = Field(default_factory=list)
    superseded_by: str | None = None
    alternatives_considered: list[str] = Field(default_factory=list)
    acceptance_criteria_met: bool = False
```

Misma estructura para los 12 tipos.

### `schemas/__init__.py`

```python
SCHEMA_BY_TYPE: dict[DocType, type[CommonFrontmatter]] = {
    DocType.SESSION: SessionFrontmatter,
    DocType.HANDOFF: HandoffFrontmatter,
    # ... 12 entradas
}

SCHEMA_BY_TYPE_ENTERPRISE: dict[DocType, type[EnterpriseFrontmatter]] = {
    DocType.SESSION: SessionFrontmatterEnterprise,
    DocType.HANDOFF: HandoffFrontmatterEnterprise,
    # ... 12 entradas
}
```

### `validation.py`

```python
def validate_frontmatter(yaml_str: str) -> CommonFrontmatter:
    """Parse YAML frontmatter and validate against the correct schema.

    Returns:
        Subclass of CommonFrontmatter (or EnterpriseFrontmatter) based on doc_type
        and vault_scope.

    Raises:
        SchemaValidationError if validation fails.
    """
    from cortex.documentation.common import yaml_load_safe
    from cortex.documentation.errors import SchemaValidationError, UnknownDocTypeError

    try:
        raw = yaml_load_safe(yaml_str)
    except Exception as e:
        raise SchemaValidationError(f"Invalid YAML: {e}") from e

    if "doc_type" not in raw:
        raise SchemaValidationError("doc_type field is required")

    try:
        doc_type = DocType(raw["doc_type"])
    except ValueError:
        raise UnknownDocTypeError(f"Unknown doc_type: {raw['doc_type']}")

    scope = raw.get("vault_scope", "local")
    if scope == "enterprise":
        schema_class = SCHEMA_BY_TYPE_ENTERPRISE[doc_type]
    elif scope == "local":
        schema_class = SCHEMA_BY_TYPE[doc_type]
    else:
        raise SchemaValidationError(f"Invalid vault_scope: {scope}")

    try:
        return schema_class.model_validate(raw)
    except ValidationError as e:
        raise SchemaValidationError(f"Frontmatter validation failed for {doc_type}: {e}") from e


def validate_path_frontmatter(path: Path) -> CommonFrontmatter:
    """Read file, extract frontmatter, validate. Convenience wrapper."""
    from cortex.documentation.common import split_frontmatter_and_body
    content = path.read_text(encoding="utf-8")
    fm_yaml, _ = split_frontmatter_and_body(content)
    return validate_frontmatter(fm_yaml)
```

---

## 4. Tests obligatorios

### Tests de DocType (`test_doc_type.py`)

```python
def test_all_doc_types_have_string_value()
def test_doc_type_enum_has_exactly_12_values()
def test_doc_type_from_str_valid()
def test_doc_type_from_str_invalid_raises()
def test_doc_type_from_path_session()
def test_doc_type_from_path_adr_prefix()
def test_doc_type_from_path_decision_non_adr()
def test_doc_type_from_path_unknown_returns_none()
def test_promotable_doc_types_excludes_handoff_and_hu()
def test_valid_statuses_has_entry_for_each_doc_type()
def test_valid_statuses_values_are_frozenset()
```

### Tests por schema (`test_schema_<type>.py`)

Patron para cada tipo (12 archivos):

```python
def test_<type>_frontmatter_minimal_valid()
def test_<type>_frontmatter_full_valid()
def test_<type>_invalid_status_raises()
def test_<type>_invalid_doc_type_in_yaml_raises()
def test_<type>_extra_fields_ignored_or_rejected()
def test_<type>_enterprise_requires_owner()
def test_<type>_serialization_roundtrip()  # model_dump -> validate -> equal
```

12 schemas x 7 tests = 84 tests minimo.

### Tests de validation (`test_validation.py`)

```python
def test_validate_routes_to_correct_schema_local()
def test_validate_routes_to_enterprise_schema()
def test_validate_missing_doc_type_raises()
def test_validate_unknown_doc_type_raises()
def test_validate_invalid_vault_scope_raises()
def test_validate_path_frontmatter_reads_file()
def test_validate_handles_malformed_yaml()
def test_validate_supports_all_12_types()  # smoke
```

---

## 5. Criterios de diseno

- **Pydantic v2.** `BaseModel`, `Field`, `model_validator`.
- **Frozen models** (`ConfigDict(frozen=True)`).
- **Discriminated union NO obligatorio.** Mas simple usar `SCHEMA_BY_TYPE` dict.
- **Email regex en `owner`:** estricto pero pragmatico.
- **Slug regex en `team`:** solo `[a-z0-9-]`.
- **Email en actor de audit:** flexible (no enforced regex; puede ser `agent-id`).
- **`fingerprint` regex strict:** 64 chars hex obligatorios.

---

## 6. Checklist

- [x] `cortex/documentation/doc_type.py` con enum de 12 + helpers
- [x] `cortex/documentation/data.py` con 12 dataclasses + CommonWriteData
- [x] `cortex/documentation/schemas/base.py` con CommonFrontmatter, EnterpriseFrontmatter, AuditEvent
- [x] 12 archivos en `cortex/documentation/schemas/` uno por tipo
- [x] `cortex/documentation/schemas/__init__.py` con SCHEMA_BY_TYPE y SCHEMA_BY_TYPE_ENTERPRISE
- [x] `cortex/documentation/validation.py` con `validate_frontmatter` y `validate_path_frontmatter`
- [x] Tests pasan al 100% (76 nuevos, 124 modulo)
- [x] Coverage >= 90% (~96% excluyendo data.py)
- [x] `from cortex.documentation.schemas import *` no rompe
- [ ] mypy verifica todo el modulo (`mypy cortex/documentation`) - PENDIENTE, no bloqueante

---

## 7. Gate de salida

- `pytest tests/unit/documentation` pasa al 100%.
- Coverage del modulo `cortex/documentation/` >= 90%.
- `mypy cortex/documentation` sin errores.
- Validator rechaza 8 casos invalidos (test_validation.py).
- `REALIZACION.md` documenta lo construido.

---

## 8. Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| Pydantic v1 vs v2 inconsistencia con otras partes del codigo | Verificar version en pyproject.toml; usar v2 syntax exclusivamente |
| Modelos enterprise duplicados (mucho boilerplate) | Aceptable; mejor explicit que magic |
| Performance de pydantic validation | Despreciable; validacion no esta en hot path |
| `datetime` timezone aware vs naive | Forzar tz-aware en validator |
| Tests de schema explotan combinatoria | Patron fijo de 7 tests por tipo limita |

---

## 9. Notas para agentes implementadores

1. **Empezar por `doc_type.py`.** Sin esto nada compila.
2. **`schemas/base.py` antes que los especificos.** Heredan de Common/Enterprise.
3. **Validator viene al final.** Necesita SCHEMA_BY_TYPE poblado.
4. **No usar discriminated union de pydantic.** Simple dict lookup es mas legible.
5. **Tests deben validar el caso bueno Y el caso malo.** No solo happy path.
6. **`frozen=True` evita bugs.** No saltearlo.
7. **No mezclar dataclasses (data.py) con pydantic models (schemas).** Son cosas distintas.

---

## 10. Referencias

- `docs/canonical-documentation/data-model.md` - especificacion completa
- `docs/canonical-documentation/frontmatter-schema.md` - YAML schemas detallados
- `docs/canonical-documentation/architecture.md` - Capa 1 y 2
