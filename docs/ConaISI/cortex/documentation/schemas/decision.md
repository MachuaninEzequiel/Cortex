# cortex/documentation/schemas/decision.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/schemas/decision.py` (22 líneas).
- **Módulo Python:** `cortex.documentation.schemas.decision`.
- **Docstring del módulo:** DECISION frontmatter schema (non-ADR decisions).
- **Clases definidas:**
  - `_DecisionSpecific` (BaseModel)
  - `DecisionFrontmatter` (_DecisionSpecific, CommonFrontmatter)
    - Decision frontmatter — campos específicos vía _DecisionSpecific (V5).
  - `DecisionFrontmatterEnterprise` (_DecisionSpecific, EnterpriseFrontmatter)
    - Decision frontmatter enterprise — hereda _DecisionSpecific + gobernanza.

## Para qué sirve

DECISION frontmatter schema (non-ADR decisions).

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
Fuente: código de `cortex/documentation/schemas/decision.py` (AST + grafo de imports internos). No se usó documentación previa.
