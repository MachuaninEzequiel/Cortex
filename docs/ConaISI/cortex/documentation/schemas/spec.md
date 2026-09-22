# cortex/documentation/schemas/spec.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/schemas/spec.py` (27 líneas).
- **Módulo Python:** `cortex.documentation.schemas.spec`.
- **Docstring del módulo:** SPEC frontmatter schema.
- **Clases definidas:**
  - `_SpecSpecific` (BaseModel)
  - `SpecFrontmatter` (_SpecSpecific, CommonFrontmatter)
    - Spec frontmatter — campos específicos vía _SpecSpecific (V5).
  - `SpecFrontmatterEnterprise` (_SpecSpecific, EnterpriseFrontmatter)
    - Spec frontmatter enterprise — hereda _SpecSpecific + gobernanza.

## Para qué sirve

SPEC frontmatter schema.

## Relaciones

### Recibe de

- `cortex.documentation.doc_type` (DocType)
- `cortex.documentation.schemas.base` (CommonFrontmatter, EnterpriseFrontmatter)
- `cortex.session.models` (VerificationHook)
- Dependencias externas/stdlib: `__future__`, `pydantic`

### Envía a

- `cortex.documentation.schemas`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 27.

---
Fuente: código de `cortex/documentation/schemas/spec.py` (AST + grafo de imports internos). No se usó documentación previa.
