# cortex/documentation/writers.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/writers.py` (787 líneas).
- **Módulo Python:** `cortex.documentation.writers`.
- **Docstring del módulo:** cortex.documentation.writers - Canonical writers for the 9 new DocTypes.
- **Clases definidas:**
  - `VaultLike` (Protocol)
    - Subset of VaultReader used by canonical writers.
    - Métodos públicos/especiales: `path`, `index_file`
- **Funciones de módulo:**
  - `_now_utc()`
  - `_default_status(doc_type)` — First valid status for ``doc_type`` (used when data.status is empty).
  - `_coerce_status(doc_type, requested)` — Return ``requested`` if valid for ``doc_type`` else first valid status.
  - `_next_number(folder, regex)` — Find the next available numeric prefix in ``folder``.
  - `_next_adr_number(vault)`
  - `_next_incident_number(vault)`
  - `_require_enterprise_fields(data, vault_scope)`
  - `_build_filename_context(data, doc_type, vault)` — Build the context dict required by ``render_filename`` for this doc_type.
  - `_common_frontmatter_fields(data, doc_type, fingerprint, vault_scope)`
  - `_enterprise_fields(data)`
  - `_type_specific_fields(data, doc_type, filename_ctx)` — Extract DocType-specific fields from ``data`` into a frontmatter dict.
  - `_build_frontmatter(data, doc_type, fingerprint, vault_scope, actor, filename_ctx)`
  - `_frontmatter_to_yaml(fm)`
  - `_write_note(path, fm, body, vault, overwrite)`
  - `_write_canonical(data, doc_type)`
  - `write_adr_note(data)` — Persist an ADR note canonically.
  - `write_decision_note(data)` — Persist a non-ADR DECISION note canonically.
  - `write_incident_note(data)` — Persist an INCIDENT note canonically.
  - `write_postmortem_note(data)` — Persist a POSTMORTEM note canonically.
  - `write_runbook_note(data)` — Persist a RUNBOOK note canonically.
  - `write_architecture_note(data)` — Persist an ARCHITECTURE note canonically.
  - `write_changelog_note(data)` — Persist a CHANGELOG entry canonically (one file per version).
  - `write_handoff_note(data)` — Persist a HANDOFF note canonically.
  - `write_glossary_entry(data)` — Persist a GLOSSARY entry canonically (one file per term).
  - `write_session_note_canonical(data)` — Persist a SESSION note canonically (Fase 04 canonical writer).
  - `write_spec_note_canonical(data)` — Persist a SPEC note canonically (Fase 04 canonical writer).
  - `write_hu_note(data)` — Persist an HU (work item) note canonically (Fase 04 canonical writer).
  - `write_design_note(data)` — Persist a DESIGN note canonically (Pluggable Middle Phase 09.B).
- **Constantes / símbolos de módulo:** `_ADR_NUM_RE`, `_INC_NUM_RE`, `__all__`

## Para qué sirve

cortex.documentation.writers - Canonical writers for the 9 new DocTypes.

Each ``write_X_note`` function follows the exact same shape:

    def write_X_note(
        data: XData,
        *,
        vault,                               # has .path: Path and .index_file(rel)
        vault_scope: str = "local",
        project_id: str | None = None,
        actor: str | None = None,
        overwrite: bool = False,
    ) -> Path:

This module covers the 9 new types from Fase 03 plus the 3 canonical writers
for the legacy SESSION / SPEC / HU types added in Fase 04
(``write_session_note_canonical``, ``write_spec_note_canonical``,
``write_hu_note``).

## Relaciones

### Recibe de

- `cortex.documentation.audit` (append_audit_event)
- `cortex.documentation.common` (compute_fingerprint, parse_frontmatter_lenient, slugify, yaml_dump_safe)
- `cortex.documentation.data` (ADRData, ArchitectureData, ChangelogData, DecisionData, DesignDocData, GlossaryEntryData, HandoffData, HUData, IncidentData, PostmortemData, RunbookData, SessionData…)
- `cortex.documentation.doc_type` (VALID_STATUSES, DocType)
- `cortex.documentation.errors` (DuplicateDocumentError, SchemaValidationError)
- `cortex.documentation.routing` (RouteSpec, resolve_route, resolve_target_path)
- `cortex.documentation.schemas` (SCHEMA_BY_TYPE, SCHEMA_BY_TYPE_ENTERPRISE, CommonFrontmatter)
- `cortex.documentation.schemas.base` (EnterpriseFrontmatter)
- `cortex.documentation.templates_engine` (render_template)
- Dependencias externas/stdlib: `re`, `__future__`, `dataclasses`, `datetime`, `pathlib`, `typing`, `pydantic`

### Envía a

- `cortex.documentation`
- `cortex.documenter.persistence`
- `cortex.services.note_service`
- `cortex.services.spec_service`
- `cortex.workitems.service`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 787.
Docstrings de símbolos públicos:
- `write_adr_note`: Persist an ADR note canonically.
- `write_decision_note`: Persist a non-ADR DECISION note canonically.
- `write_incident_note`: Persist an INCIDENT note canonically.
- `write_postmortem_note`: Persist a POSTMORTEM note canonically.
- `write_runbook_note`: Persist a RUNBOOK note canonically.
- `write_architecture_note`: Persist an ARCHITECTURE note canonically.
- `write_changelog_note`: Persist a CHANGELOG entry canonically (one file per version).
- `write_handoff_note`: Persist a HANDOFF note canonically.
- `write_glossary_entry`: Persist a GLOSSARY entry canonically (one file per term).
- `write_session_note_canonical`: Persist a SESSION note canonically (Fase 04 canonical writer).
- `write_spec_note_canonical`: Persist a SPEC note canonically (Fase 04 canonical writer).
- `write_hu_note`: Persist an HU (work item) note canonically (Fase 04 canonical writer).

---
Fuente: código de `cortex/documentation/writers.py` (AST + grafo de imports internos). No se usó documentación previa.
