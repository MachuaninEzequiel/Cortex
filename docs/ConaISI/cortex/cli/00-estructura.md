# Estructura — `cortex/cli`

## Para qué existe esta carpeta

(sin docstring de paquete; reexportes)

## Árbol interno (código, sin `__pycache__`)

```
cli/
├── __init__.py
├── _search_filters.py
├── _setup_helpers.py
├── _unicode_fallback.py
├── ci.py
├── common.py
├── docs_migrate.py
├── docs_search.py
├── docs_subcommand.py
├── docs_vectorization.py
├── documenting.py
├── embedding.py
├── hu.py
├── ide.py
├── main.py
├── mcp_cmd.py
├── next.py
├── pr_context.py
├── review_knowledge.py
├── session.py
└── session_tui.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/cli/__init__.py` | 4 | reexportes / marcador de paquete |
| `cortex/cli/_search_filters.py` | 104 | Shared helper to build ``EnrichmentFilters`` from CLI/MCP flags. |
| `cortex/cli/_setup_helpers.py` | 66 | cortex.cli._setup_helpers ------------------------- Helpers compartidos por los comandos ``cortex setup *``. |
| `cortex/cli/_unicode_fallback.py` | 64 | Cross-platform glyph helpers — fallback to ASCII when the console encoding cannot render unicode (e.g. ``cmd.exe`` defaulting to cp1252). |
| `cortex/cli/ci.py` | 287 | ``cortex ci`` — CI plugin subapp (Pluggable Middle Phase 07). |
| `cortex/cli/common.py` | 97 | Plomería compartida entre los submódulos de ``cortex.cli``. |
| `cortex/cli/docs_migrate.py` | 161 | cortex.cli.docs_migrate - ``cortex docs migrate/validate/restore`` (Fase 11). |
| `cortex/cli/docs_search.py` | 125 | cortex.cli.docs_search - ``cortex docs search`` with structural filters (Fase 13). |
| `cortex/cli/docs_subcommand.py` | 134 | cortex.cli.docs_subcommand - ``cortex docs`` subcommand group. |
| `cortex/cli/docs_vectorization.py` | 122 | cortex.cli.docs_vectorization - ``cortex docs vectorization`` subcommands. |
| `cortex/cli/documenting.py` | 372 | ``save-session`` / ``create-spec`` / ``finish-session`` — flujo documental. |
| `cortex/cli/embedding.py` | 216 | ``cortex embedding-status`` y ``cortex reindex`` — superficie de embeddings. |
| `cortex/cli/hu.py` | 51 | ``cortex hu`` — gestión de work items trackeados (import read-only). |
| `cortex/cli/ide.py` | 377 | ``cortex ide`` — unified CLI surface for IDE adapters (Obra 02, Fase 3). |
| `cortex/cli/main.py` | 1932 | cortex.cli.main --------------- Command-line interface for Cortex (Typer). |
| `cortex/cli/mcp_cmd.py` | 49 | ``cortex mcp-server`` — servidor MCP sobre stdio. |
| `cortex/cli/next.py` | 138 | ``cortex next`` — lista de acciones sugeridas sin TUI (Obra 05 Fase B). |
| `cortex/cli/pr_context.py` | 249 | ``cortex pr-context`` — pipeline DevSecDocOps (captura → docs → memoria). |
| `cortex/cli/review_knowledge.py` | 216 | cortex.cli.review_knowledge - Manage the promotion review queue. |
| `cortex/cli/session.py` | 846 | ``cortex session`` — user-facing CLI for the Session primitive. |
| `cortex/cli/session_tui.py` | 735 | ``cortex session watch`` — live TUI for the Session primitive. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.action_engine.actions`
- `cortex.action_engine.context`
- `cortex.action_engine.scheduler`
- `cortex.autopilot.cli`
- `cortex.brain.cli`
- `cortex.ci.diff_io`
- `cortex.ci.markdown_formatter`
- `cortex.ci.result`
- `cortex.ci.validator`
- `cortex.cli._search_filters`
- `cortex.cli._unicode_fallback`
- `cortex.cli.ci`
- `cortex.cli.common`
- `cortex.cli.docs_migrate`
- `cortex.cli.docs_search`
- `cortex.cli.docs_subcommand`
- `cortex.cli.docs_vectorization`
- `cortex.cli.documenting`
- `cortex.cli.embedding`
- `cortex.cli.hu`
- `cortex.cli.ide`
- `cortex.cli.main`
- `cortex.cli.mcp_cmd`
- `cortex.cli.next`
- `cortex.cli.pr_context`
- `cortex.cli.review_knowledge`
- `cortex.cli.session`
- `cortex.context_enricher.config`
- `cortex.context_enricher.enricher`
- `cortex.context_enricher.filters`
- `cortex.context_enricher.presenter`
- `cortex.core`
- `cortex.documentation.backup`
- `cortex.documentation.doc_type`
- `cortex.documentation.errors`
- `cortex.documentation.migration`
- `cortex.documentation.routing`
- `cortex.enterprise.promotion_doctype`
- `cortex.ide`
- `cortex.ide.base`
- `cortex.ide.registry`
- `cortex.semantic.vector_cache`
- `cortex.session`
- `cortex.session.errors`
- `cortex.session.git`
- `cortex.session.hooks`
- `cortex.session.models`
- `cortex.session.service`
- `cortex.session.storage`
- `cortex.session.verification`
- `cortex.webgraph.cli`
- `cortex.workspace.layout`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.cli`
- `cortex.cli.docs_search`
- `cortex.cli.docs_subcommand`
- `cortex.cli.documenting`
- `cortex.cli.embedding`
- `cortex.cli.hu`
- `cortex.cli.main`
- `cortex.cli.pr_context`
- `cortex.cli.session_tui`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
