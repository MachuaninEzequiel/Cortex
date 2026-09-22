# cortex/documentation/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/__init__.py` (148 líneas).
- **Módulo Python:** `cortex.documentation`.
- **Docstring del módulo:** cortex.documentation - Canonical documentation system.
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.documentation - Canonical documentation system.

This package provides the canonical documentation primitives used across Cortex:
DocType enum, frontmatter schemas, routing table, and canonical writers.

The package is structured in layered modules:

- ``errors`` - Exception hierarchy.
- ``common`` - Shared helpers (slugify, fingerprint, YAML safe ops).
- ``inventory`` - Vault scanning utilities used by migration tooling.
- ``doc_type`` - DocType enum + VALID_STATUSES + helpers (Fase 01).
- ``data`` - Dataclasses for writer inputs (Fase 01).
- ``schemas/`` - Pydantic frontmatter schemas (Fase 01).
- ``validation`` - Public frontmatter validator (Fase 01).
- ``routing`` - DOC_TYPE_ROUTING table + RouteSpec + helpers (Fase 02).
- ``templates_engine`` - Jinja2 renderer (Fase 03).
- ``audit`` - Enterprise audit_trail helper (Fase 03).
- ``writers`` - Canonical writers, 12 functions (Fase 03 + Fase 04).

Consumers build the canonical dataclass (``SessionData``, ``SpecData``,
``HUData``, etc.) from ``cortex.documentation.data`` and pass it directly
to the matching ``write_*_note`` canonical writer.

## Relaciones

### Recibe de

- `cortex.documentation.common` (compute_fingerprint, has_frontmatter, parse_frontmatter_lenient, slugify, split_frontmatter_and_body, yaml_dump_safe, yaml_load_safe)
- `cortex.documentation.doc_type` (DocType)
- `cortex.documentation.errors` (DocumentationError, DuplicateDocumentError, RoutingError, SchemaValidationError, TemplateRenderError, UnknownDocTypeError)
- `cortex.documentation.inventory` (VaultInventory, classify_path, inventory_vault)
- `cortex.documentation.routing` (DOC_TYPE_ROUTING)
- `cortex.documentation.writers` (write_adr_note, write_architecture_note, write_changelog_note, write_decision_note, write_design_note, write_design_note_canonical, write_glossary_entry, write_handoff_note, write_hu_note, write_incident_note, write_postmortem_note, write_runbook_note…)
- Dependencias externas/stdlib: `__future__`, `dataclasses`

### Envía a

- `cortex.services.note_service`
- `cortex.services.spec_service`
- `cortex.workitems.service`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 148.
Reexportes observados:
- cortex.documentation.common: compute_fingerprint, has_frontmatter, parse_frontmatter_lenient, slugify, split_frontmatter_and_body, yaml_dump_safe, yaml_load_safe
- cortex.documentation.doc_type: DocType
- cortex.documentation.errors: DocumentationError, DuplicateDocumentError, RoutingError, SchemaValidationError, TemplateRenderError, UnknownDocTypeError
- cortex.documentation.inventory: VaultInventory, classify_path, inventory_vault
- cortex.documentation.routing: DOC_TYPE_ROUTING
- cortex.documentation.writers: write_adr_note, write_architecture_note, write_changelog_note, write_decision_note, write_design_note, write_design_note_canonical, write_glossary_entry, write_handoff_note, write_hu_note, write_incident_note, write_postmortem_note, write_runbook_note, write_session_note_canonical, write_spec_note_canonical

---
Fuente: código de `cortex/documentation/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
