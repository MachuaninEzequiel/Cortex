# cortex/documentation/schemas/runbook.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/schemas/runbook.py` (52 líneas).
- **Módulo Python:** `cortex.documentation.schemas.runbook`.
- **Docstring del módulo:** RUNBOOK frontmatter schema.
- **Clases definidas:**
  - `_RunbookSpecific` (BaseModel)
  - `RunbookFrontmatter` (_RunbookSpecific, CommonFrontmatter)
    - Runbook frontmatter — campos específicos vía _RunbookSpecific (V5).
  - `RunbookFrontmatterEnterprise` (_RunbookSpecific, EnterpriseFrontmatter)
    - Runbook frontmatter enterprise — hereda _RunbookSpecific + gobernanza.
- **Funciones de módulo:**
  - `_validate_kind(v)`
  - `_validate_tz(v)`
- **Constantes / símbolos de módulo:** `_RUNBOOK_KINDS`

## Para qué sirve

RUNBOOK frontmatter schema.

## Relaciones

### Recibe de

- `cortex.documentation.doc_type` (DocType)
- `cortex.documentation.schemas.base` (CommonFrontmatter, EnterpriseFrontmatter)
- Dependencias externas/stdlib: `__future__`, `datetime`, `pydantic`

### Envía a

- `cortex.documentation.schemas`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 52.

---
Fuente: código de `cortex/documentation/schemas/runbook.py` (AST + grafo de imports internos). No se usó documentación previa.
