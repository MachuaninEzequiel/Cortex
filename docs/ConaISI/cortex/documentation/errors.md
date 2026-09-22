# cortex/documentation/errors.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/errors.py` (28 líneas).
- **Módulo Python:** `cortex.documentation.errors`.
- **Docstring del módulo:** cortex.documentation.errors - Exception hierarchy for the documentation module.
- **Clases definidas:**
  - `DocumentationError` (Exception)
    - Base error for cortex.documentation.
  - `SchemaValidationError` (DocumentationError)
    - Frontmatter does not validate against schema.
  - `UnknownDocTypeError` (DocumentationError)
    - doc_type value is not a member of the DocType enum.
  - `RoutingError` (DocumentationError)
    - RouteSpec resolution or path rendering failed.
  - `DuplicateDocumentError` (DocumentationError)
    - Document already exists at target path and overwrite=False.
  - `TemplateRenderError` (DocumentationError)
    - Jinja2 template render failed.

## Para qué sirve

cortex.documentation.errors - Exception hierarchy for the documentation module.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `__future__`

### Envía a

- `cortex.cli.docs_subcommand`
- `cortex.documentation`
- `cortex.documentation.doc_type`
- `cortex.documentation.routing`
- `cortex.documentation.templates_engine`
- `cortex.documentation.validation`
- `cortex.documentation.writers`
- `cortex.enterprise.promotion_doctype`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 28.

---
Fuente: código de `cortex/documentation/errors.py` (AST + grafo de imports internos). No se usó documentación previa.
