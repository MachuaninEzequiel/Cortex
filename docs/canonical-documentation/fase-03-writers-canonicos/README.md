# Fase 03 - Writers Canonicos Nuevos

**Fuente:** `docs/canonical-documentation/README.md`
**Estado:** Completada (2026-05-14) - ver [`REALIZACION.md`](REALIZACION.md)
**Esfuerzo estimado:** 2.5 dias (real: ~2 horas)
**Riesgo:** medio
**Dependencias:** Fase 01, Fase 02

---

## 1. Objetivo

Implementar la **Capa 4 (Writers canonicos)** para los 9 tipos faltantes:
- `write_adr_note`
- `write_decision_note`
- `write_incident_note`
- `write_postmortem_note`
- `write_runbook_note`
- `write_architecture_note`
- `write_changelog_note`
- `write_handoff_note`
- `write_glossary_entry`

Mas los 12 templates Jinja2 correspondientes (incluyendo los 3 existentes: session, spec, hu).

Esta es la fase que "cierra la promesa de las carpetas" - cada carpeta del routing table tendra ahora un escritor canonico.

---

## 2. Archivos a crear

```text
cortex/documentation/
    writers.py                       # NUEVO: 9 writers + helpers comunes
    templates_engine.py              # NUEVO: render_template helper
    templates/
        session.md.j2                # NUEVO
        handoff.md.j2                # NUEVO
        spec.md.j2                   # NUEVO
        adr.md.j2                    # NUEVO
        decision.md.j2               # NUEVO
        incident.md.j2               # NUEVO
        postmortem.md.j2             # NUEVO
        runbook.md.j2                # NUEVO
        architecture.md.j2           # NUEVO
        changelog.md.j2              # NUEVO
        hu.md.j2                     # NUEVO
        glossary.md.j2               # NUEVO

cortex/documentation/
    audit.py                          # NUEVO: append_audit_event helper

tests/unit/documentation/
    test_write_adr_note.py
    test_write_decision_note.py
    test_write_incident_note.py
    test_write_postmortem_note.py
    test_write_runbook_note.py
    test_write_architecture_note.py
    test_write_changelog_note.py
    test_write_handoff_note.py
    test_write_glossary_entry.py
    test_writers_common.py             # tests de helpers compartidos
    test_audit.py
    templates/
        test_session_template.py
        test_handoff_template.py
        test_spec_template.py
        test_adr_template.py
        test_decision_template.py
        test_incident_template.py
        test_postmortem_template.py
        test_runbook_template.py
        test_architecture_template.py
        test_changelog_template.py
        test_hu_template.py
        test_glossary_template.py

tests/integration/documentation/
    test_writers_e2e.py                # write -> index -> search
```

---

## 3. Responsabilidades

### `templates_engine.py`

```python
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateError
from pathlib import Path
from cortex.documentation.errors import TemplateRenderError

TEMPLATES_DIR = Path(__file__).parent / "templates"

_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(disabled_extensions=("md.j2",)),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)


def render_template(template_name: str, data: dict) -> str:
    """Render a Jinja2 template with data dict."""
    try:
        template = _env.get_template(template_name)
        return template.render(**data)
    except TemplateError as e:
        raise TemplateRenderError(f"Failed to render {template_name}: {e}") from e
```

### `audit.py`

```python
def append_audit_event(
    frontmatter: EnterpriseFrontmatter,
    actor: str,
    action: str,
    reason: str | None = None,
) -> EnterpriseFrontmatter:
    """Return a new EnterpriseFrontmatter with appended audit event.

    Audit trail is append-only; never removes existing events.
    """
    new_event = AuditEvent(
        actor=actor,
        action=action,
        timestamp=datetime.now(UTC),
        reason=reason,
    )
    updated = frontmatter.model_dump()
    updated["audit_trail"] = list(frontmatter.audit_trail) + [new_event.model_dump()]
    return type(frontmatter).model_validate(updated)
```

### `writers.py`

Patron canonico por writer:

```python
def write_X_note(
    data: XData,
    *,
    vault: VaultReader,
    vault_scope: str = "local",
    project_id: str | None = None,
    actor: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Persist X note canonically.

    Steps:
        1. Validate data.
        2. Resolve route from DOC_TYPE_ROUTING.
        3. Render template body.
        4. Compute fingerprint.
        5. Build frontmatter (Common or Enterprise).
        6. Render full markdown.
        7. Resolve target path.
        8. Check duplicate (unless overwrite=True).
        9. Persist.
        10. Index incrementally.
        11. Audit event if enterprise.
        12. Return absolute path.
    """
    # 1. Validate
    _validate_data(data, DocType.X)
    if vault_scope == "enterprise":
        if not data.owner or not data.team:
            raise SchemaValidationError("owner and team required for enterprise")

    # 2. Resolve route
    route = resolve_route(DocType.X)

    # 3. Render body
    body = render_template(route.template_path.name, asdict(data))

    # 4. Fingerprint
    fingerprint = compute_fingerprint(body)

    # 5. Build frontmatter
    now = datetime.now(UTC)
    fm_dict = {
        "schema_version": 1,
        "doc_type": DocType.X.value,
        "title": data.title,
        "created_at": now,
        "updated_at": now,
        "tags": data.tags,
        "status": data.status or _default_status(DocType.X),
        "links": data.links,
        "vault_scope": vault_scope,
        "fingerprint": fingerprint,
    }
    # Campos especificos por tipo
    fm_dict.update(_type_specific_fields(data, DocType.X))

    if vault_scope == "enterprise":
        fm_dict.update({
            "owner": data.owner,
            "team": data.team,
            "classification": data.classification or "internal",
            "retention_days": data.retention_days or 0,
            "audit_trail": [],
        })
        # Validar contra EnterpriseFrontmatter
        fm = SCHEMA_BY_TYPE_ENTERPRISE[DocType.X].model_validate(fm_dict)
        # Agregar evento "created"
        fm = append_audit_event(fm, actor or "unknown", "created")
    else:
        fm = SCHEMA_BY_TYPE[DocType.X].model_validate(fm_dict)

    # 6. Render full markdown
    fm_yaml = yaml_dump_safe(fm.model_dump(mode="json"))
    full_md = "---\n" + fm_yaml + "---\n\n" + body

    # 7. Resolve path
    context = _build_filename_context(data)
    target = resolve_target_path(route, context, vault.path, vault_scope, project_id)

    # 8. Check duplicate
    if target.exists() and not overwrite:
        raise DuplicateDocumentError(f"Already exists: {target}")

    # 9. Persist
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(full_md, encoding="utf-8")

    # 10. Index
    rel_path = str(target.relative_to(vault.path))
    vault.index_file(rel_path)

    return target
```

Variantes especificas:

- `write_adr_note` auto-asigna `adr_number` si es 0: busca el siguiente disponible en `decisions/`.
- `write_incident_note` auto-asigna `incident_number` similar.
- `write_postmortem_note` requiere `incident_path` valido apuntando a un INCIDENT existente.
- `write_handoff_note` no se promueve nunca (`vault_scope` siempre `local`); raise si se intenta enterprise.

### Templates `.md.j2`

Contenido completo en `docs/canonical-documentation/templates-reference.md`. Crear los 12 archivos con el contenido alli especificado.

---

## 4. Helpers comunes en `writers.py`

```python
def _build_filename_context(data: CommonWriteData, doc_type: DocType) -> dict:
    """Build context dict for filename_template.format()."""
    from cortex.documentation.common import slugify

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    ctx = {
        "date": today,
        "slug": slugify(data.title),
    }
    if doc_type == DocType.ADR:
        ctx["number"] = data.adr_number
    elif doc_type == DocType.INCIDENT:
        ctx["number"] = data.incident_number
    elif doc_type == DocType.POSTMORTEM:
        ctx["incident_number"] = data.incident_number
    elif doc_type == DocType.SESSION:
        ctx["session_id"] = data.session_id
    elif doc_type == DocType.HU:
        ctx["external_id"] = data.external_id
    elif doc_type == DocType.GLOSSARY:
        ctx["term-slug"] = slugify(data.term)
    elif doc_type == DocType.CHANGELOG:
        ctx["version"] = data.version
    return ctx


def _next_adr_number(vault: VaultReader) -> int:
    """Find next available ADR number in vault/decisions/."""
    decisions_dir = vault.path / "decisions"
    if not decisions_dir.exists():
        return 1
    existing = []
    for path in decisions_dir.glob("ADR-*.md"):
        m = re.match(r"ADR-(\d+)", path.stem)
        if m:
            existing.append(int(m.group(1)))
    return (max(existing) + 1) if existing else 1


def _next_incident_number(vault: VaultReader) -> int:
    """Find next available incident number."""
    incidents_dir = vault.path / "incidents"
    if not incidents_dir.exists():
        return 1
    existing = []
    for path in incidents_dir.glob("INC-*.md"):
        m = re.match(r"INC-(\d+)", path.stem)
        if m:
            existing.append(int(m.group(1)))
    return (max(existing) + 1) if existing else 1


def _default_status(doc_type: DocType) -> str:
    """Pick first valid status for doc_type."""
    return next(iter(VALID_STATUSES[doc_type]))


def _type_specific_fields(data, doc_type: DocType) -> dict:
    """Extract fields specific to doc_type from data dataclass."""
    if doc_type == DocType.ADR:
        return {
            "adr_number": data.adr_number,
            "supersedes": data.supersedes,
            "superseded_by": data.superseded_by,
            "alternatives_considered": data.alternatives_considered,
            "acceptance_criteria_met": data.acceptance_criteria_met,
        }
    elif doc_type == DocType.INCIDENT:
        return {
            "incident_number": data.incident_number,
            "severity": data.severity,
            "opened_at": data.opened_at or datetime.now(UTC),
            "closed_at": data.closed_at,
            "affected_services": data.affected_services,
            "root_cause_postmortem": data.root_cause_postmortem,
        }
    # ... etc por tipo
    return {}
```

---

## 5. Tests por writer

Patron de 8 tests por writer (9 writers * 8 = 72 tests minimo):

```python
# tests/unit/documentation/test_write_adr_note.py

def test_write_adr_minimal(tmp_vault):
    """Minimum required fields."""
    data = ADRData(
        title="Use ONNX",
        context="ctx", decision="dec", consequences="cons",
        alternatives_considered=["sentence-transformers"],
        adr_number=1,
    )
    path = write_adr_note(data, vault=tmp_vault)
    assert path.exists()
    assert path.name == "ADR-001-use-onnx.md"
    content = path.read_text()
    assert "doc_type: adr" in content
    assert "## Decision" in content


def test_write_adr_auto_assigns_number(tmp_vault_with_adrs):
    """If adr_number=0, auto-assign next."""
    data = ADRData(title="New", context="c", decision="d", consequences="cs", adr_number=0)
    path = write_adr_note(data, vault=tmp_vault_with_adrs)
    # Asumiendo que el vault ya tiene ADR-001, ADR-002 -> nuevo es 003
    assert path.stem.startswith("ADR-003-")


def test_write_adr_duplicate_raises(tmp_vault):
    """Same number twice raises."""
    data = ADRData(title="X", context="c", decision="d", consequences="cs", adr_number=5)
    write_adr_note(data, vault=tmp_vault)
    with pytest.raises(DuplicateDocumentError):
        write_adr_note(data, vault=tmp_vault)


def test_write_adr_overwrite_allowed(tmp_vault):
    """overwrite=True allows duplicate."""
    data = ADRData(...)
    write_adr_note(data, vault=tmp_vault)
    write_adr_note(data, vault=tmp_vault, overwrite=True)  # no raise


def test_write_adr_invalid_data_raises(tmp_vault):
    """Empty title raises."""
    data = ADRData(title="", ...)
    with pytest.raises(SchemaValidationError):
        write_adr_note(data, vault=tmp_vault)


def test_write_adr_indexes_file(tmp_vault):
    """Written file is in vault index."""
    path = write_adr_note(data, vault=tmp_vault)
    rel = str(path.relative_to(tmp_vault.path))
    assert rel in tmp_vault._index


def test_write_adr_fingerprint_deterministic(tmp_vault):
    """Same content -> same fingerprint."""
    data1 = ADRData(...)
    data2 = ADRData(...)  # mismo contenido
    p1 = write_adr_note(data1, vault=tmp_vault, overwrite=True)
    fm1 = parse_frontmatter(p1)
    p2 = write_adr_note(data2, vault=tmp_vault, overwrite=True)
    fm2 = parse_frontmatter(p2)
    assert fm1.fingerprint == fm2.fingerprint


def test_write_adr_enterprise(tmp_vault):
    """Enterprise scope produces EnterpriseFrontmatter."""
    data = ADRData(..., owner="a@b.com", team="t")
    path = write_adr_note(
        data, vault=tmp_vault, vault_scope="enterprise", project_id="proj",
        actor="user@example.com",
    )
    content = path.read_text()
    assert "owner: a@b.com" in content
    assert "team: t" in content
    assert "audit_trail:" in content
    assert "action: created" in content
```

Mismo patron para cada uno de los otros 8 writers, con sus variantes (postmortem requiere `incident_path`, handoff no acepta enterprise scope, etc).

### Tests de templates (`templates/test_<type>_template.py`)

Por template (12 archivos * 4 tests = 48 tests):

```python
def test_<type>_template_minimal():
    """Renders with min required fields."""

def test_<type>_template_full():
    """All optional sections rendered."""

def test_<type>_template_empty_list_omits_section():
    """If list is empty, section omitted."""

def test_<type>_template_special_chars_in_title():
    """Title with quotes/markdown chars renders cleanly."""
```

### Tests de integracion (`test_writers_e2e.py`)

```python
def test_write_adr_then_search_finds_it(tmp_vault):
    """ADR written is searchable."""

def test_write_runbook_then_enrich_includes_it(tmp_vault, enricher):
    """Enricher picks up new runbook on relevant query."""

def test_write_session_then_validate_frontmatter(tmp_vault):
    """Session note frontmatter validates against schema."""

def test_write_then_reindex_consistent(tmp_vault):
    """After write + reindex, vault state consistent."""
```

---

## 6. Asignacion de writers a routing table

En Fase 02 los writers quedaron como `None`. Ahora se asignan:

```python
# cortex/documentation/routing.py - UPDATE

from cortex.documentation.writers import (
    write_session_note, write_handoff_note, write_spec_note,
    write_adr_note, write_decision_note, write_incident_note,
    write_postmortem_note, write_runbook_note, write_architecture_note,
    write_changelog_note, write_hu_note, write_glossary_entry,
)

DOC_TYPE_ROUTING: dict[DocType, RouteSpec] = {
    DocType.SESSION: RouteSpec(..., writer=write_session_note, ...),
    DocType.HANDOFF: RouteSpec(..., writer=write_handoff_note, ...),
    # ...
}
```

Nota: `write_session_note` y `write_spec_note` y `write_hu_note` se migran en Fase 04; aqui se referencian sus stubs.

---

## 7. Criterios de diseno

- **Firma simetrica:** los 9 writers tienen exactamente la misma signature.
- **Templates externos:** todos los templates en `.md.j2`, no inline.
- **Validacion al inicio:** falla antes de tocar disco.
- **Index automatico:** sin paso manual.
- **Auto-asignacion de numbers:** ADR/incident no piden manual al usuario; opt-in con `0`.
- **Duplicate raise default:** sobrescritura explicita con `overwrite=True`.
- **Audit trail solo enterprise:** writer local no toca audit_trail.
- **Datetime con timezone UTC** siempre.
- **YAML order:** preservar orden de insercion para legibilidad.

---

## 8. Checklist

- [x] `cortex/documentation/templates_engine.py` con `render_template`
- [x] `cortex/documentation/audit.py` con `append_audit_event`
- [x] `cortex/documentation/writers.py` con 9 nuevos writers + helpers
- [x] 12 templates `.md.j2` en `cortex/documentation/templates/`
- [x] Asignacion de los 9 writers nuevos a `DOC_TYPE_ROUTING` (legacy 3 quedan a Fase 04)
- [x] Tests por writer (37 tests en `test_writers.py` cubriendo 9 writers)
- [x] Tests por template (8 tests en `test_templates_engine.py` cubriendo 12 templates)
- [x] Tests integracion / round-trip (1 test verifica los 9 writers contra schema)
- [x] Coverage >= 90% (~97%)
- [x] `cortex docs routing-table` muestra 9 writers asignados (3 legacy aun None)

---

## 9. Gate de salida

- `pytest tests/unit/documentation/test_write_*` pasa al 100%.
- `pytest tests/unit/documentation/templates/` pasa al 100%.
- `pytest tests/integration/documentation/test_writers_e2e.py` pasa al 100%.
- Coverage del modulo `cortex/documentation/` >= 90%.
- Cada writer puede crear su tipo de doc valido (no SchemaValidationError en happy path).
- `cortex docs routing-table` muestra los 12 writers definidos.
- `REALIZACION.md` documentado.

---

## 10. Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| 9 writers x boilerplate inflate el modulo | Helpers compartidos (`_build_filename_context`, `_type_specific_fields`) |
| Templates Jinja inconsistentes entre tipos | Test por template + convencion clara en `templates-reference.md` |
| Numeracion ADR race condition (concurrencia) | Lock por carpeta; explicit in docstring |
| `write_session_note` legacy no esta migrado aun (Fase 04) | Stub temporal en routing que apunta a la version legacy |
| Postmortem requiere INCIDENT que no existe | Validacion: si `incident_path` no existe, raise con sugerencia |
| Handoff promovido por error | Validacion: handoff con scope=enterprise raise |
| Glossary slug colision para terminos con mismo slug | Suffix `-2` automatico |
| Performance de jinja render | Jinja cachea templates; despreciable |

---

## 11. Notas para agentes implementadores

1. **Empezar por `templates_engine.py` y `audit.py`.** Helpers base.
2. **Implementar UN writer completo (ej ADR) con todos los tests** antes de pasar al siguiente. Patron estable, replicable.
3. **Templates en archivos separados desde el inicio.** No inline.
4. **`_type_specific_fields` puede crecer.** Aceptable; alternativa (polimorfismo) es overkill.
5. **Tests de templates verifican OUTPUT,** no implementacion.
6. **No skippear tests "porque obvio".** Cada caso falla en produccion alguna vez.
7. **`SchemaValidationError` con mensaje claro.** Documenter agent lo va a leer.
8. **Cuidado con tz-aware datetimes.** Mezclar naive y aware rompe pydantic.

---

## 12. Referencias

- `docs/canonical-documentation/data-model.md` - dataclasses
- `docs/canonical-documentation/frontmatter-schema.md` - schema completo
- `docs/canonical-documentation/templates-reference.md` - 12 templates
- `docs/canonical-documentation/routing-table.md` - tabla de routing
- `docs/canonical-documentation/architecture.md` - Capa 4
