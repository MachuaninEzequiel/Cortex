# cortex/documentation/schemas/changelog.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/schemas/changelog.py` (33 líneas).
- **Módulo Python:** `cortex.documentation.schemas.changelog`.
- **Docstring del módulo:** CHANGELOG frontmatter schema.
- **Clases definidas:**
  - `_ChangelogSpecific` (BaseModel)
  - `ChangelogFrontmatter` (_ChangelogSpecific, CommonFrontmatter)
    - Changelog frontmatter — campos específicos vía _ChangelogSpecific (V5).
  - `ChangelogFrontmatterEnterprise` (_ChangelogSpecific, EnterpriseFrontmatter)
    - Changelog frontmatter enterprise — hereda _ChangelogSpecific + gobernanza.
- **Funciones de módulo:**
  - `_validate_tz(v)`

## Para qué sirve

CHANGELOG frontmatter schema.

## Relaciones

### Recibe de

- `cortex.documentation.doc_type` (DocType)
- `cortex.documentation.schemas.base` (CommonFrontmatter, EnterpriseFrontmatter)
- Dependencias externas/stdlib: `__future__`, `datetime`, `pydantic`

### Envía a

- `cortex.documentation.schemas`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 33.

---
Fuente: código de `cortex/documentation/schemas/changelog.py` (AST + grafo de imports internos). No se usó documentación previa.
