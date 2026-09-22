# cortex/documentation/schemas/hu.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/schemas/hu.py` (46 líneas).
- **Módulo Python:** `cortex.documentation.schemas.hu`.
- **Docstring del módulo:** HU (user story / work item) frontmatter schema.
- **Clases definidas:**
  - `_HUSpecific` (BaseModel)
  - `HUFrontmatter` (_HUSpecific, CommonFrontmatter)
    - HU frontmatter — campos específicos vía _HUSpecific (V5).
  - `HUFrontmatterEnterprise` (_HUSpecific, EnterpriseFrontmatter)
    - HU frontmatter enterprise — hereda _HUSpecific + gobernanza.
- **Funciones de módulo:**
  - `_validate_kind(v)`
  - `_validate_tz(v)`
- **Constantes / símbolos de módulo:** `_HU_KINDS`

## Para qué sirve

HU (user story / work item) frontmatter schema.

## Relaciones

### Recibe de

- `cortex.documentation.doc_type` (DocType)
- `cortex.documentation.schemas.base` (CommonFrontmatter, EnterpriseFrontmatter)
- Dependencias externas/stdlib: `__future__`, `datetime`, `pydantic`

### Envía a

- `cortex.documentation.schemas`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 46.

---
Fuente: código de `cortex/documentation/schemas/hu.py` (AST + grafo de imports internos). No se usó documentación previa.
