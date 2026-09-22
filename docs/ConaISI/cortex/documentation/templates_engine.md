# cortex/documentation/templates_engine.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/templates_engine.py` (51 líneas).
- **Módulo Python:** `cortex.documentation.templates_engine`.
- **Docstring del módulo:** cortex.documentation.templates_engine - Jinja2 renderer for canonical templates.
- **Funciones de módulo:**
  - `_build_environment()` — Construct the Jinja2 environment used to render canonical templates.
  - `render_template(template_name, data)` — Render the named Jinja2 template with ``data`` as the context dict.
- **Constantes / símbolos de módulo:** `TEMPLATES_DIR`

## Para qué sirve

cortex.documentation.templates_engine - Jinja2 renderer for canonical templates.

Templates live in ``cortex/documentation/templates/*.md.j2``. They render the
*body* of a markdown note; the frontmatter is built and prepended by the writer.

## Relaciones

### Recibe de

- `cortex.documentation.errors` (TemplateRenderError)
- Dependencias externas/stdlib: `__future__`, `pathlib`, `typing`, `jinja2`

### Envía a

- `cortex.documentation.writers`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 51.
Docstrings de símbolos públicos:
- `render_template`: Render the named Jinja2 template with ``data`` as the context dict.

---
Fuente: código de `cortex/documentation/templates_engine.py` (AST + grafo de imports internos). No se usó documentación previa.
