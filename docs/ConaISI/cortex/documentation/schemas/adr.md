# cortex/documentation/schemas/adr.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/schemas/adr.py` (26 líneas).
- **Módulo Python:** `cortex.documentation.schemas.adr`.
- **Docstring del módulo:** ADR frontmatter schema.
- **Clases definidas:**
  - `_ADRSpecific` (BaseModel)
  - `ADRFrontmatter` (_ADRSpecific, CommonFrontmatter)
    - ADR frontmatter — campos específicos vía _ADRSpecific (V5).
  - `ADRFrontmatterEnterprise` (_ADRSpecific, EnterpriseFrontmatter)
    - ADR frontmatter enterprise — hereda _ADRSpecific + gobernanza.

## Para qué sirve

ADR frontmatter schema.

## Relaciones

### Recibe de

- `cortex.documentation.doc_type` (DocType)
- `cortex.documentation.schemas.base` (CommonFrontmatter, EnterpriseFrontmatter)
- Dependencias externas/stdlib: `__future__`, `pydantic`

### Envía a

- `cortex.documentation.schemas`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 26.

---
Fuente: código de `cortex/documentation/schemas/adr.py` (AST + grafo de imports internos). No se usó documentación previa.
