# cortex/documentation/doc_type.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/doc_type.py` (203 líneas).
- **Módulo Python:** `cortex.documentation.doc_type`.
- **Docstring del módulo:** cortex.documentation.doc_type - DocType enum and helpers.
- **Clases definidas:**
  - `DocType` (str, Enum)
    - Canonical document types in Cortex.
- **Funciones de módulo:**
  - `doc_type_from_str(value)` — Parse a string to its DocType enum member.
  - `infer_doc_type_from_path(path)` — Canonical DocType inference (Fase 13).
  - `doc_type_from_path(path)` — Infer the DocType from a markdown file's path.
  - `all_doc_types()` — Return all DocType enum members in declaration order.
  - `promotable_doc_types()` — Return doc types that can be promoted to enterprise vault.
- **Constantes / símbolos de módulo:** `VALID_STATUSES`, `_PROMOTABLE`, `_SUBFOLDER_TO_DOC_TYPE`, `_ADR_FILENAME_RE`

## Para qué sirve

cortex.documentation.doc_type - DocType enum and helpers.

The ``DocType`` enum is a closed list of 12 canonical document types in
Cortex. Any extension requires an ADR.

This module is the foundation of the canonical documentation system: all
schemas, routing, writers, retrieval filters and webgraph styling reference
``DocType`` values.

## Relaciones

### Recibe de

- `cortex.documentation.errors` (UnknownDocTypeError)
- Dependencias externas/stdlib: `re`, `__future__`, `enum`, `pathlib`

### Envía a

- `cortex.cli._search_filters`
- `cortex.cli.docs_subcommand`
- `cortex.context_enricher.filters`
- `cortex.documentation`
- `cortex.documentation.migration`
- `cortex.documentation.routing`
- `cortex.documentation.schemas`
- `cortex.documentation.schemas.adr`
- `cortex.documentation.schemas.architecture`
- `cortex.documentation.schemas.base`
- `cortex.documentation.schemas.changelog`
- `cortex.documentation.schemas.decision`
- `cortex.documentation.schemas.design`
- `cortex.documentation.schemas.glossary`
- `cortex.documentation.schemas.handoff`
- `cortex.documentation.schemas.hu`
- `cortex.documentation.schemas.incident`
- `cortex.documentation.schemas.postmortem`
- `cortex.documentation.schemas.runbook`
- `cortex.documentation.schemas.session`
- `cortex.documentation.schemas.spec`
- `cortex.documentation.validation`
- `cortex.documentation.writers`
- `cortex.enterprise.promotion_doctype`
- `cortex.semantic.chunker`
- `cortex.semantic.vault_reader`
- `cortex.webgraph.style`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 203.
Docstrings de símbolos públicos:
- `doc_type_from_str`: Parse a string to its DocType enum member.
- `infer_doc_type_from_path`: Canonical DocType inference (Fase 13).
- `doc_type_from_path`: Infer the DocType from a markdown file's path.
- `all_doc_types`: Return all DocType enum members in declaration order.
- `promotable_doc_types`: Return doc types that can be promoted to enterprise vault.

---
Fuente: código de `cortex/documentation/doc_type.py` (AST + grafo de imports internos). No se usó documentación previa.
