# cortex/enterprise/models.py

## Qué tiene adentro

- **Ruta de código:** `cortex/enterprise/models.py` (184 líneas).
- **Módulo Python:** `cortex.enterprise.models`.
- **Clases definidas:**
  - `OrganizationConfig` (BaseModel)
    - Métodos internos: `_normalize_slug`
  - `MemoryConfig` (BaseModel)
    - Métodos internos: `_validate_paths`
  - `PromotionConfig` (BaseModel)
  - `GovernanceConfig` (BaseModel)
  - `IntegrationConfig` (BaseModel)
  - `TeamConfig` (BaseModel)
    - A team inside the organization.
  - `RetentionPolicy` (BaseModel)
    - Default retention in days per DocType. ``0`` means no expiration.
    - Métodos públicos/especiales: `for_doc_type`
  - `EnterprisePolicies` (BaseModel)
    - Free-form policies applied across the org.
  - `EnterpriseOrgConfig` (BaseModel)
    - Métodos públicos/especiales: `resolve_enterprise_vault_path`, `resolve_enterprise_memory_path`
    - Métodos internos: `_validate_cross_section_rules`

## Para qué sirve

Define OrganizationConfig, MemoryConfig, PromotionConfig, GovernanceConfig, IntegrationConfig, TeamConfig, RetentionPolicy, EnterprisePolicies, EnterpriseOrgConfig. No hay docstring de módulo; el propósito se infiere de las clases y métodos listados.

## Relaciones

### Recibe de

- `cortex.runtime_context` (slugify)
- Dependencias externas/stdlib: `__future__`, `pathlib`, `typing`, `pydantic`

### Envía a

- `cortex.doctor`
- `cortex.enterprise`
- `cortex.enterprise.config`
- `cortex.enterprise.governance`
- `cortex.enterprise.maintenance`
- `cortex.enterprise.promotion_doctype`
- `cortex.enterprise.retrieval_service`
- `cortex.setup.orchestrator`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 184.
Docstrings de símbolos públicos:
- `RetentionPolicy.for_doc_type`: Return the retention days for a doc_type slug. Unknown -> 0.
- `EnterpriseOrgConfig.resolve_enterprise_vault_path`: Resolve the enterprise vault path.
- `EnterpriseOrgConfig.resolve_enterprise_memory_path`: Resolve the enterprise memory path.

---
Fuente: código de `cortex/enterprise/models.py` (AST + grafo de imports internos). No se usó documentación previa.
