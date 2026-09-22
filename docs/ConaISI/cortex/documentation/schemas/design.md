# cortex/documentation/schemas/design.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/schemas/design.py` (30 líneas).
- **Módulo Python:** `cortex.documentation.schemas.design`.
- **Docstring del módulo:** DESIGN frontmatter schema (Pluggable Middle Phase 09.B).
- **Clases definidas:**
  - `_DesignSpecific` (BaseModel)
  - `DesignFrontmatter` (_DesignSpecific, CommonFrontmatter)
    - Design frontmatter — campos específicos vía _DesignSpecific (V5).
  - `DesignFrontmatterEnterprise` (_DesignSpecific, EnterpriseFrontmatter)
    - Design frontmatter enterprise — hereda _DesignSpecific + gobernanza.

## Para qué sirve

DESIGN frontmatter schema (Pluggable Middle Phase 09.B).

The ``design`` doc type captures the architecture / data-model / API
contract / test-plan decisions taken **before** implementation. Written
by the ``cortex-code-designer`` subagent in Deep Track. Linked back to
both the originating spec and the open Session via ``spec_path`` and
``session_id``.

## Relaciones

### Recibe de

- `cortex.documentation.doc_type` (DocType)
- `cortex.documentation.schemas.base` (CommonFrontmatter, EnterpriseFrontmatter)
- Dependencias externas/stdlib: `__future__`, `pydantic`

### Envía a

- `cortex.documentation.schemas`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 30.

---
Fuente: código de `cortex/documentation/schemas/design.py` (AST + grafo de imports internos). No se usó documentación previa.
