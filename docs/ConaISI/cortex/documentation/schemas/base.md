# cortex/documentation/schemas/base.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/schemas/base.py` (136 líneas).
- **Módulo Python:** `cortex.documentation.schemas.base`.
- **Docstring del módulo:** Base pydantic models for canonical frontmatter.
- **Clases definidas:**
  - `CommonFrontmatter` (BaseModel)
    - Canonical frontmatter shared by all DocTypes.
    - Métodos internos: `_validate_tz_aware`, `_validate_vault_scope`, `_validate_dates_order`, `_validate_status_for_doc_type`
  - `AuditEvent` (BaseModel)
    - A single entry in the audit_trail (enterprise only).
    - Métodos internos: `_validate_tz_aware`
  - `EnterpriseFrontmatter` (CommonFrontmatter)
    - Frontmatter required when ``vault_scope='enterprise'``.
    - Métodos internos: `_validate_classification`, `_validate_enterprise_scope`
- **Funciones de módulo:**
  - `_get_classifications()`
  - `_get_vault_scopes()`
- **Constantes / símbolos de módulo:** `_VAULT_SCOPES`, `_CLASSIFICATIONS`, `_FINGERPRINT_PATTERN`, `_EMAIL_PATTERN`, `_TEAM_PATTERN`, `__all__`

## Para qué sirve

Base pydantic models for canonical frontmatter.

## Relaciones

### Recibe de

- `cortex.documentation.doc_type` (VALID_STATUSES, DocType)
- Dependencias externas/stdlib: `__future__`, `datetime`, `pydantic`

### Envía a

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
- `cortex.documentation.writers`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 136.

---
Fuente: código de `cortex/documentation/schemas/base.py` (AST + grafo de imports internos). No se usó documentación previa.
