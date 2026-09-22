# cortex/documentation/schemas/incident.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/schemas/incident.py` (47 líneas).
- **Módulo Python:** `cortex.documentation.schemas.incident`.
- **Docstring del módulo:** INCIDENT frontmatter schema.
- **Clases definidas:**
  - `_IncidentSpecific` (BaseModel)
  - `IncidentFrontmatter` (_IncidentSpecific, CommonFrontmatter)
    - Incident frontmatter — campos específicos vía _IncidentSpecific (V5).
  - `IncidentFrontmatterEnterprise` (_IncidentSpecific, EnterpriseFrontmatter)
    - Incident frontmatter enterprise — hereda _IncidentSpecific + gobernanza.
- **Funciones de módulo:**
  - `_validate_severity(v)`
  - `_validate_tz(v)`
- **Constantes / símbolos de módulo:** `_SEVERITIES`

## Para qué sirve

INCIDENT frontmatter schema.

## Relaciones

### Recibe de

- `cortex.documentation.doc_type` (DocType)
- `cortex.documentation.schemas.base` (CommonFrontmatter, EnterpriseFrontmatter)
- Dependencias externas/stdlib: `__future__`, `datetime`, `pydantic`

### Envía a

- `cortex.documentation.schemas`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 47.

---
Fuente: código de `cortex/documentation/schemas/incident.py` (AST + grafo de imports internos). No se usó documentación previa.
