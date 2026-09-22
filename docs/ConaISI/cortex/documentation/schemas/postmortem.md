# cortex/documentation/schemas/postmortem.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/schemas/postmortem.py` (34 líneas).
- **Módulo Python:** `cortex.documentation.schemas.postmortem`.
- **Docstring del módulo:** POSTMORTEM frontmatter schema.
- **Clases definidas:**
  - `_PostmortemSpecific` (BaseModel)
  - `PostmortemFrontmatter` (_PostmortemSpecific, CommonFrontmatter)
    - Postmortem frontmatter — campos específicos vía _PostmortemSpecific (V5).
  - `PostmortemFrontmatterEnterprise` (_PostmortemSpecific, EnterpriseFrontmatter)
    - Postmortem frontmatter enterprise — hereda _PostmortemSpecific + gobernanza.
- **Funciones de módulo:**
  - `_validate_severity(v)`
- **Constantes / símbolos de módulo:** `_SEVERITIES`

## Para qué sirve

POSTMORTEM frontmatter schema.

## Relaciones

### Recibe de

- `cortex.documentation.doc_type` (DocType)
- `cortex.documentation.schemas.base` (CommonFrontmatter, EnterpriseFrontmatter)
- Dependencias externas/stdlib: `__future__`, `pydantic`

### Envía a

- `cortex.documentation.schemas`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 34.

---
Fuente: código de `cortex/documentation/schemas/postmortem.py` (AST + grafo de imports internos). No se usó documentación previa.
