# cortex/documentation/routing.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documentation/routing.py` (429 líneas).
- **Módulo Python:** `cortex.documentation.routing`.
- **Docstring del módulo:** cortex.documentation.routing - Canonical routing table for DocTypes.
- **Clases definidas:**
  - `RouteSpec`
    - Routing specification for a single DocType.
- **Funciones de módulo:**
  - `resolve_route(doc_type)` — Look up the canonical RouteSpec for a DocType.
  - `render_filename(spec, context)` — Render ``spec.filename_template`` with ``context``.
  - `resolve_target_path(spec, context, vault_root, vault_scope, project_id)` — Resolve the absolute target path for a note inside the vault.
  - `list_all_routes()` — Return all RouteSpecs in DOC_TYPE_ROUTING (declaration order).
  - `routes_by_subfolder()` — Group RouteSpecs by their ``subfolder`` value.
- **Constantes / símbolos de módulo:** `TEMPLATES_DIR`, `DOC_TYPE_ROUTING`, `_PLACEHOLDER_RE`

## Para qué sirve

cortex.documentation.routing - Canonical routing table for DocTypes.

The ``DOC_TYPE_ROUTING`` dict is the *single source of truth* for:
- which subfolder each DocType lives in,
- how filenames are rendered,
- which Jinja2 template renders the body,
- which writer function persists the note,
- whether the note is promotable to enterprise (and how),
- chunking and retrieval boost configuration,
- webgraph styling.

The ``writer`` field is filled in by Fase 03 (canonical writers). For Fase 02
it is set to ``None`` for the 9 new types; the 3 legacy types (session, spec,
hu) reference the legacy shim re-exported via ``cortex.documentation``.

## Relaciones

### Recibe de

- `cortex.documentation.doc_type` (DocType)
- `cortex.documentation.errors` (RoutingError, UnknownDocTypeError)
- Dependencias externas/stdlib: `re`, `__future__`, `collections.abc`, `dataclasses`, `pathlib`, `typing`

### Envía a

- `cortex.cli.docs_subcommand`
- `cortex.documentation`
- `cortex.documentation.writers`
- `cortex.enterprise.promotion_doctype`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 429.
Docstrings de símbolos públicos:
- `resolve_route`: Look up the canonical RouteSpec for a DocType.
- `render_filename`: Render ``spec.filename_template`` with ``context``.
- `resolve_target_path`: Resolve the absolute target path for a note inside the vault.
- `list_all_routes`: Return all RouteSpecs in DOC_TYPE_ROUTING (declaration order).
- `routes_by_subfolder`: Group RouteSpecs by their ``subfolder`` value.

---
Fuente: código de `cortex/documentation/routing.py` (AST + grafo de imports internos). No se usó documentación previa.
