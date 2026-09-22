# Estructura — `cortex/documentation/schemas`

## Para qué existe esta carpeta

cortex.documentation.schemas - Pydantic models for frontmatter validation.

## Árbol interno (código, sin `__pycache__`)

```
schemas/
├── __init__.py
├── adr.py
├── architecture.py
├── base.py
├── changelog.py
├── decision.py
├── design.py
├── glossary.py
├── handoff.py
├── hu.py
├── incident.py
├── postmortem.py
├── runbook.py
├── session.py
└── spec.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
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

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.documentation.doc_type`
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
- `cortex.session.models`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.documentation.audit`
- `cortex.documentation.schemas`
- `cortex.documentation.schemas.adr`
- `cortex.documentation.schemas.architecture`
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

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
