# cortex/cli/docs_subcommand.py

## Qué tiene adentro

- **Ruta de código:** `cortex/cli/docs_subcommand.py` (134 líneas).
- **Módulo Python:** `cortex.cli.docs_subcommand`.
- **Docstring del módulo:** cortex.cli.docs_subcommand - ``cortex docs`` subcommand group.
- **Funciones de módulo:**
  - `_docs_main()` — Canonical documentation system commands.
  - `_spec_to_serializable(spec)` — Convert a RouteSpec to a JSON-friendly dict.
  - `routing_table(doc_type, json_output)` — Print the canonical DOC_TYPE_ROUTING table.

## Para qué sirve

cortex.cli.docs_subcommand - ``cortex docs`` subcommand group.

In Fase 02 this group exposes a single command, ``routing-table``, which
inspects the canonical routing table. Later phases add ``validate``,
``migrate``, ``vectorization``, ``schema``, ``scaffold``, etc.

## Relaciones

### Recibe de

- `cortex.documentation.doc_type` (DocType)
- `cortex.documentation.errors` (UnknownDocTypeError)
- `cortex.documentation.routing` (list_all_routes, resolve_route)
- `cortex.cli.docs_vectorization` (app)
- `cortex.cli.docs_migrate` (list_backups_cmd)
- `cortex.cli.docs_migrate` (migrate)
- `cortex.cli.docs_migrate` (restore)
- `cortex.cli.docs_migrate` (validate)
- `cortex.cli.docs_search` (search)
- Dependencias externas/stdlib: `json`, `typer`, `__future__`, `dataclasses`

### Envía a

- `cortex.cli.main`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 134.
Docstrings de símbolos públicos:
- `routing_table`: Print the canonical DOC_TYPE_ROUTING table.

---
Fuente: código de `cortex/cli/docs_subcommand.py` (AST + grafo de imports internos). No se usó documentación previa.
