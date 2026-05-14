"""cortex.documentation - Canonical documentation system.

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
- ``_legacy_shims`` - Backwards-compatible wrappers (Fase 04, removed in Fase 12).

The 3 legacy writers (``write_session_note``, ``write_spec_note``,
``write_tracked_item_note``) keep their original signatures via
``_legacy_shims`` while internally delegating to the canonical writers.
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace

from cortex.documentation.errors import (
    DocumentationError,
    DuplicateDocumentError,
    RoutingError,
    SchemaValidationError,
    TemplateRenderError,
    UnknownDocTypeError,
)
from cortex.documentation.common import (
    compute_fingerprint,
    has_frontmatter,
    parse_frontmatter_lenient,
    slugify,
    split_frontmatter_and_body,
    yaml_dump_safe,
    yaml_load_safe,
)
from cortex.documentation.inventory import (
    VaultInventory,
    classify_path,
    inventory_vault,
)
from cortex.documentation.doc_type import DocType as _DocType
from cortex.documentation.routing import DOC_TYPE_ROUTING as _DOC_TYPE_ROUTING

# Canonical writers (Fase 03 + Fase 04).
from cortex.documentation.writers import (
    write_adr_note,
    write_architecture_note,
    write_changelog_note,
    write_decision_note,
    write_glossary_entry,
    write_handoff_note,
    write_hu_note,
    write_incident_note,
    write_postmortem_note,
    write_runbook_note,
    write_session_note_canonical,
    write_spec_note_canonical,
)

# Legacy-shaped wrappers (Fase 04). Re-exported as ``write_session_note``,
# ``write_spec_note``, ``write_tracked_item_note`` for backwards
# compatibility with existing consumers.
from cortex.documentation._legacy_shims import (
    write_session_note,
    write_spec_note,
    write_tracked_item_note,
)


# Bind the 12 canonical writers to their RouteSpec entries.
_DOC_TYPE_ROUTING[_DocType.SESSION] = _dc_replace(
    _DOC_TYPE_ROUTING[_DocType.SESSION], writer=write_session_note_canonical
)
_DOC_TYPE_ROUTING[_DocType.SPEC] = _dc_replace(
    _DOC_TYPE_ROUTING[_DocType.SPEC], writer=write_spec_note_canonical
)
_DOC_TYPE_ROUTING[_DocType.HU] = _dc_replace(
    _DOC_TYPE_ROUTING[_DocType.HU], writer=write_hu_note
)
_DOC_TYPE_ROUTING[_DocType.ADR] = _dc_replace(
    _DOC_TYPE_ROUTING[_DocType.ADR], writer=write_adr_note
)
_DOC_TYPE_ROUTING[_DocType.DECISION] = _dc_replace(
    _DOC_TYPE_ROUTING[_DocType.DECISION], writer=write_decision_note
)
_DOC_TYPE_ROUTING[_DocType.INCIDENT] = _dc_replace(
    _DOC_TYPE_ROUTING[_DocType.INCIDENT], writer=write_incident_note
)
_DOC_TYPE_ROUTING[_DocType.POSTMORTEM] = _dc_replace(
    _DOC_TYPE_ROUTING[_DocType.POSTMORTEM], writer=write_postmortem_note
)
_DOC_TYPE_ROUTING[_DocType.RUNBOOK] = _dc_replace(
    _DOC_TYPE_ROUTING[_DocType.RUNBOOK], writer=write_runbook_note
)
_DOC_TYPE_ROUTING[_DocType.ARCHITECTURE] = _dc_replace(
    _DOC_TYPE_ROUTING[_DocType.ARCHITECTURE], writer=write_architecture_note
)
_DOC_TYPE_ROUTING[_DocType.CHANGELOG] = _dc_replace(
    _DOC_TYPE_ROUTING[_DocType.CHANGELOG], writer=write_changelog_note
)
_DOC_TYPE_ROUTING[_DocType.HANDOFF] = _dc_replace(
    _DOC_TYPE_ROUTING[_DocType.HANDOFF], writer=write_handoff_note
)
_DOC_TYPE_ROUTING[_DocType.GLOSSARY] = _dc_replace(
    _DOC_TYPE_ROUTING[_DocType.GLOSSARY], writer=write_glossary_entry
)


__all__ = [
    # Errors
    "DocumentationError",
    "DuplicateDocumentError",
    "RoutingError",
    "SchemaValidationError",
    "TemplateRenderError",
    "UnknownDocTypeError",
    # Common helpers
    "compute_fingerprint",
    "has_frontmatter",
    "parse_frontmatter_lenient",
    "slugify",
    "split_frontmatter_and_body",
    "yaml_dump_safe",
    "yaml_load_safe",
    # Inventory
    "VaultInventory",
    "classify_path",
    "inventory_vault",
    # Legacy-shaped writers (preserved for backwards compatibility)
    "write_session_note",
    "write_spec_note",
    "write_tracked_item_note",
    # Canonical writers (Fase 03 + Fase 04)
    "write_adr_note",
    "write_decision_note",
    "write_incident_note",
    "write_postmortem_note",
    "write_runbook_note",
    "write_architecture_note",
    "write_changelog_note",
    "write_handoff_note",
    "write_glossary_entry",
    "write_hu_note",
    "write_session_note_canonical",
    "write_spec_note_canonical",
]
