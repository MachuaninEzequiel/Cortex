# cortex/documentation/schemas/session.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/schemas/session.py` (58 líneas).
- **Módulo Python:** `cortex.documentation.schemas.session`.
- **Docstring del módulo:** SESSION frontmatter schema.
- **Clases definidas:**
  - `CortexTelemetry` (BaseModel)
    - Telemetry block embedded in session frontmatter (Fase 05).
  - `_SessionFields` (BaseModel)
    - Fields specific to SESSION (mixed into both local and enterprise).
  - `_SessionSpecific` (BaseModel)
  - `SessionFrontmatter` (_SessionSpecific, CommonFrontmatter)
    - Session frontmatter — campos específicos vía _SessionSpecific (V5).
  - `SessionFrontmatterEnterprise` (_SessionSpecific, EnterpriseFrontmatter)
    - Session frontmatter enterprise — hereda _SessionSpecific + gobernanza.

## Para qué sirve

SESSION frontmatter schema.

## Relaciones

### Recibe de

- `cortex.documentation.doc_type` (DocType)
- `cortex.documentation.schemas.base` (CommonFrontmatter, EnterpriseFrontmatter)
- Dependencias externas/stdlib: `__future__`, `typing`, `pydantic`

### Envía a

- `cortex.documentation.schemas`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 58.

---
Fuente: código de `cortex/documentation/schemas/session.py` (AST + grafo de imports internos). No se usó documentación previa.
