# cortex/documentation/schemas/glossary.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/schemas/glossary.py` (24 líneas).
- **Módulo Python:** `cortex.documentation.schemas.glossary`.
- **Docstring del módulo:** GLOSSARY frontmatter schema.
- **Clases definidas:**
  - `_GlossarySpecific` (BaseModel)
  - `GlossaryFrontmatter` (_GlossarySpecific, CommonFrontmatter)
    - Glossary frontmatter — campos específicos vía _GlossarySpecific (V5).
  - `GlossaryFrontmatterEnterprise` (_GlossarySpecific, EnterpriseFrontmatter)
    - Glossary frontmatter enterprise — hereda _GlossarySpecific + gobernanza.

## Para qué sirve

GLOSSARY frontmatter schema.

## Relaciones

### Recibe de

- `cortex.documentation.doc_type` (DocType)
- `cortex.documentation.schemas.base` (CommonFrontmatter, EnterpriseFrontmatter)
- Dependencias externas/stdlib: `__future__`, `pydantic`

### Envía a

- `cortex.documentation.schemas`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 24.

---
Fuente: código de `cortex/documentation/schemas/glossary.py` (AST + grafo de imports internos). No se usó documentación previa.
