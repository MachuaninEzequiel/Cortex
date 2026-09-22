# cortex/documentation/schemas/architecture.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/schemas/architecture.py` (22 líneas).
- **Módulo Python:** `cortex.documentation.schemas.architecture`.
- **Docstring del módulo:** ARCHITECTURE frontmatter schema.
- **Clases definidas:**
  - `_ArchitectureSpecific` (BaseModel)
  - `ArchitectureFrontmatter` (_ArchitectureSpecific, CommonFrontmatter)
    - Architecture frontmatter — campos específicos vía _ArchitectureSpecific (V5).
  - `ArchitectureFrontmatterEnterprise` (_ArchitectureSpecific, EnterpriseFrontmatter)
    - Architecture frontmatter enterprise — hereda _ArchitectureSpecific + gobernanza.

## Para qué sirve

ARCHITECTURE frontmatter schema.

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
Fuente: código de `cortex/documentation/schemas/architecture.py` (AST + grafo de imports internos). No se usó documentación previa.
