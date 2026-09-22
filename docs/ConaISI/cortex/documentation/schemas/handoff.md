# cortex/documentation/schemas/handoff.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/schemas/handoff.py` (22 líneas).
- **Módulo Python:** `cortex.documentation.schemas.handoff`.
- **Docstring del módulo:** HANDOFF frontmatter schema.
- **Clases definidas:**
  - `_HandoffSpecific` (BaseModel)
  - `HandoffFrontmatter` (_HandoffSpecific, CommonFrontmatter)
    - Handoff frontmatter — campos específicos vía _HandoffSpecific (V5).
  - `HandoffFrontmatterEnterprise` (_HandoffSpecific, EnterpriseFrontmatter)
    - Handoff frontmatter enterprise — hereda _HandoffSpecific + gobernanza.

## Para qué sirve

HANDOFF frontmatter schema.

## Relaciones

### Recibe de

- `cortex.documentation.doc_type` (DocType)
- `cortex.documentation.schemas.base` (CommonFrontmatter, EnterpriseFrontmatter)
- Dependencias externas/stdlib: `__future__`, `pydantic`

### Envía a

- `cortex.documentation.schemas`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 22.

---
Fuente: código de `cortex/documentation/schemas/handoff.py` (AST + grafo de imports internos). No se usó documentación previa.
