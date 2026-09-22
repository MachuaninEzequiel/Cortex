# cortex/documentation/schemas/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/schemas/__init__.py` (136 líneas).
- **Módulo Python:** `cortex.documentation.schemas`.
- **Docstring del módulo:** cortex.documentation.schemas - Pydantic models for frontmatter validation.
- **Constantes / símbolos de módulo:** `SCHEMA_BY_TYPE`, `SCHEMA_BY_TYPE_ENTERPRISE`, `__all__`

## Para qué sirve

cortex.documentation.schemas - Pydantic models for frontmatter validation.

Exports:
    - Base models: CommonFrontmatter, EnterpriseFrontmatter, AuditEvent.
    - 12 type-specific models (CommonFrontmatter + EnterpriseFrontmatter pair each).
    - SCHEMA_BY_TYPE: lookup map DocType -> CommonFrontmatter subclass.
    - SCHEMA_BY_TYPE_ENTERPRISE: lookup map DocType -> EnterpriseFrontmatter subclass.

## Relaciones

### Recibe de

- `cortex.documentation.doc_type` (DocType)
- `cortex.documentation.schemas.adr` (ADRFrontmatter, ADRFrontmatterEnterprise)
- `cortex.documentation.schemas.architecture` (ArchitectureFrontmatter, ArchitectureFrontmatterEnterprise)
- `cortex.documentation.schemas.base` (AuditEvent, CommonFrontmatter, EnterpriseFrontmatter)
- `cortex.documentation.schemas.changelog` (ChangelogFrontmatter, ChangelogFrontmatterEnterprise)
- `cortex.documentation.schemas.decision` (DecisionFrontmatter, DecisionFrontmatterEnterprise)
- `cortex.documentation.schemas.design` (DesignFrontmatter, DesignFrontmatterEnterprise)
- `cortex.documentation.schemas.glossary` (GlossaryFrontmatter, GlossaryFrontmatterEnterprise)
- `cortex.documentation.schemas.handoff` (HandoffFrontmatter, HandoffFrontmatterEnterprise)
- `cortex.documentation.schemas.hu` (HUFrontmatter, HUFrontmatterEnterprise)
- `cortex.documentation.schemas.incident` (IncidentFrontmatter, IncidentFrontmatterEnterprise)
- `cortex.documentation.schemas.postmortem` (PostmortemFrontmatter, PostmortemFrontmatterEnterprise)
- `cortex.documentation.schemas.runbook` (RunbookFrontmatter, RunbookFrontmatterEnterprise)
- `cortex.documentation.schemas.session` (CortexTelemetry, SessionFrontmatter, SessionFrontmatterEnterprise)
- `cortex.documentation.schemas.spec` (SpecFrontmatter, SpecFrontmatterEnterprise)
- Dependencias externas/stdlib: `__future__`

### Envía a

- `cortex.documentation.audit`
- `cortex.documentation.validation`
- `cortex.documentation.writers`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 136.
Reexportes observados:
- cortex.documentation.doc_type: DocType
- cortex.documentation.schemas.adr: ADRFrontmatter, ADRFrontmatterEnterprise
- cortex.documentation.schemas.architecture: ArchitectureFrontmatter, ArchitectureFrontmatterEnterprise
- cortex.documentation.schemas.base: AuditEvent, CommonFrontmatter, EnterpriseFrontmatter
- cortex.documentation.schemas.changelog: ChangelogFrontmatter, ChangelogFrontmatterEnterprise
- cortex.documentation.schemas.decision: DecisionFrontmatter, DecisionFrontmatterEnterprise
- cortex.documentation.schemas.design: DesignFrontmatter, DesignFrontmatterEnterprise
- cortex.documentation.schemas.glossary: GlossaryFrontmatter, GlossaryFrontmatterEnterprise
- cortex.documentation.schemas.handoff: HandoffFrontmatter, HandoffFrontmatterEnterprise
- cortex.documentation.schemas.hu: HUFrontmatter, HUFrontmatterEnterprise
- cortex.documentation.schemas.incident: IncidentFrontmatter, IncidentFrontmatterEnterprise
- cortex.documentation.schemas.postmortem: PostmortemFrontmatter, PostmortemFrontmatterEnterprise
- cortex.documentation.schemas.runbook: RunbookFrontmatter, RunbookFrontmatterEnterprise
- cortex.documentation.schemas.session: CortexTelemetry, SessionFrontmatter, SessionFrontmatterEnterprise
- cortex.documentation.schemas.spec: SpecFrontmatter, SpecFrontmatterEnterprise

---
Fuente: código de `cortex/documentation/schemas/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
