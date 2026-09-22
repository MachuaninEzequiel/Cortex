# cortex/documentation/validation.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/validation.py` (91 líneas).
- **Módulo Python:** `cortex.documentation.validation`.
- **Docstring del módulo:** cortex.documentation.validation - Public validator for frontmatter.
- **Funciones de módulo:**
  - `validate_frontmatter(yaml_str)` — Parse a YAML frontmatter string and validate against the canonical schema.
  - `validate_path_frontmatter(path)` — Read a markdown file, extract its frontmatter, and validate.

## Para qué sirve

cortex.documentation.validation - Public validator for frontmatter.

Parses YAML frontmatter and validates it against the correct pydantic schema
based on ``doc_type`` and ``vault_scope``.

## Relaciones

### Recibe de

- `cortex.documentation.common` (split_frontmatter_and_body, yaml_load_safe)
- `cortex.documentation.doc_type` (DocType)
- `cortex.documentation.errors` (SchemaValidationError, UnknownDocTypeError)
- `cortex.documentation.schemas` (SCHEMA_BY_TYPE, SCHEMA_BY_TYPE_ENTERPRISE, CommonFrontmatter)
- Dependencias externas/stdlib: `yaml`, `__future__`, `pathlib`, `pydantic`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 91.
Docstrings de símbolos públicos:
- `validate_frontmatter`: Parse a YAML frontmatter string and validate against the canonical schema.
- `validate_path_frontmatter`: Read a markdown file, extract its frontmatter, and validate.

---
Fuente: código de `cortex/documentation/validation.py` (AST + grafo de imports internos). No se usó documentación previa.
