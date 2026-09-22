# Estructura — `cortex/documentation`

## Para qué existe esta carpeta

cortex.documentation - Canonical documentation system.

## Árbol interno (código, sin `__pycache__`)

```
documentation/
├── schemas/
│   ├── __init__.py
│   ├── adr.py
│   ├── architecture.py
│   ├── base.py
│   ├── changelog.py
│   ├── decision.py
│   ├── design.py
│   ├── glossary.py
│   ├── handoff.py
│   ├── hu.py
│   ├── incident.py
│   ├── postmortem.py
│   ├── runbook.py
│   ├── session.py
│   └── spec.py
├── templates/
│   ├── adr.md.j2
│   ├── architecture.md.j2
│   ├── changelog.md.j2
│   ├── decision.md.j2
│   ├── design.md.j2
│   ├── glossary.md.j2
│   ├── handoff.md.j2
│   ├── hu.md.j2
│   ├── incident.md.j2
│   ├── postmortem.md.j2
│   ├── runbook.md.j2
│   ├── session.md.j2
│   └── spec.md.j2
├── __init__.py
├── audit.py
├── backup.py
├── common.py
├── data.py
├── doc_type.py
├── errors.py
├── inventory.py
├── migration.py
├── routing.py
├── templates_engine.py
├── validation.py
└── writers.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/documentation/__init__.py` | 148 | cortex.documentation - Canonical documentation system. |
| `cortex/documentation/audit.py` | 45 | cortex.documentation.audit - Helpers for enterprise audit_trail. |
| `cortex/documentation/backup.py` | 102 | cortex.documentation.backup - Tar.gz backup helpers for migrate operations. |
| `cortex/documentation/common.py` | 139 | cortex.documentation.common - Shared helpers used across documentation layers. |
| `cortex/documentation/data.py` | 223 | cortex.documentation.data - Dataclasses for writer inputs. |
| `cortex/documentation/doc_type.py` | 203 | cortex.documentation.doc_type - DocType enum and helpers. |
| `cortex/documentation/errors.py` | 28 | cortex.documentation.errors - Exception hierarchy for the documentation module. |
| `cortex/documentation/inventory.py` | 130 | cortex.documentation.inventory - Scan the vault to produce a diagnostic snapshot. |
| `cortex/documentation/migration.py` | 566 | cortex.documentation.migration - Vault backfill to the canonical schema. |
| `cortex/documentation/routing.py` | 429 | cortex.documentation.routing - Canonical routing table for DocTypes. |
| `cortex/documentation/schemas/__init__.py` | 136 | cortex.documentation.schemas - Pydantic models for frontmatter validation. |
| `cortex/documentation/schemas/adr.py` | 26 | ADR frontmatter schema. |
| `cortex/documentation/schemas/architecture.py` | 22 | ARCHITECTURE frontmatter schema. |
| `cortex/documentation/schemas/base.py` | 136 | Base pydantic models for canonical frontmatter. |
| `cortex/documentation/schemas/changelog.py` | 33 | CHANGELOG frontmatter schema. |
| `cortex/documentation/schemas/decision.py` | 22 | DECISION frontmatter schema (non-ADR decisions). |
| `cortex/documentation/schemas/design.py` | 30 | DESIGN frontmatter schema (Pluggable Middle Phase 09.B). |
| `cortex/documentation/schemas/glossary.py` | 24 | GLOSSARY frontmatter schema. |
| `cortex/documentation/schemas/handoff.py` | 22 | HANDOFF frontmatter schema. |
| `cortex/documentation/schemas/hu.py` | 46 | HU (user story / work item) frontmatter schema. |
| `cortex/documentation/schemas/incident.py` | 47 | INCIDENT frontmatter schema. |
| `cortex/documentation/schemas/postmortem.py` | 34 | POSTMORTEM frontmatter schema. |
| `cortex/documentation/schemas/runbook.py` | 52 | RUNBOOK frontmatter schema. |
| `cortex/documentation/schemas/session.py` | 58 | SESSION frontmatter schema. |
| `cortex/documentation/schemas/spec.py` | 27 | SPEC frontmatter schema. |
| `cortex/documentation/templates_engine.py` | 51 | cortex.documentation.templates_engine - Jinja2 renderer for canonical templates. |
| `cortex/documentation/validation.py` | 91 | cortex.documentation.validation - Public validator for frontmatter. |
| `cortex/documentation/writers.py` | 787 | cortex.documentation.writers - Canonical writers for the 9 new DocTypes. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.documentation.audit`
- `cortex.documentation.backup`
- `cortex.documentation.common`
- `cortex.documentation.data`
- `cortex.documentation.doc_type`
- `cortex.documentation.errors`
- `cortex.documentation.inventory`
- `cortex.documentation.routing`
- `cortex.documentation.schemas`
- `cortex.documentation.schemas.base`
- `cortex.documentation.templates_engine`
- `cortex.documentation.writers`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.cli._search_filters`
- `cortex.cli.docs_migrate`
- `cortex.cli.docs_subcommand`
- `cortex.context_enricher.filters`
- `cortex.documentation`
- `cortex.documentation.doc_type`
- `cortex.documentation.inventory`
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
- `cortex.documentation.templates_engine`
- `cortex.documentation.validation`
- `cortex.documentation.writers`
- `cortex.documenter.persistence`
- `cortex.documenter.spec_loader`
- `cortex.enterprise.maintenance`
- `cortex.enterprise.promotion_doctype`
- `cortex.semantic.chunker`
- `cortex.semantic.vault_reader`
- `cortex.services.note_service`
- `cortex.services.spec_service`
- `cortex.webgraph.style`
- `cortex.workitems.service`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
