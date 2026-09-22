# cortex/context_enricher/presenter.py

## Qué tiene adentro

- **Ruta de código:** `cortex/context_enricher/presenter.py` (241 líneas).
- **Módulo Python:** `cortex.context_enricher.presenter`.
- **Docstring del módulo:** cortex.context_enricher.presenter ----------------------------------- Formats EnrichedContext for different output targets:   - Markdown: human-readable for PR comments   - Compact: single-line format for LLM prompt injection   - JSON: structured for CI/CD pipelines
- **Clases definidas:**
  - `ContextPresenter`
    - Formats enriched context for different consumers.
    - Métodos públicos/especiales: `to_markdown`, `to_compact`, `to_markdown_grouped`, `to_compact_grouped`, `to_json`

## Para qué sirve

cortex.context_enricher.presenter
-----------------------------------
Formats EnrichedContext for different output targets:
  - Markdown: human-readable for PR comments
  - Compact: single-line format for LLM prompt injection
  - JSON: structured for CI/CD pipelines

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `json`, `__future__`, `typing`

### Envía a

- `cortex.cli.docs_search`
- `cortex.context_enricher`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 241.
Docstrings de símbolos públicos:
- `ContextPresenter.to_markdown`: Format as human-readable markdown for PR comments.
- `ContextPresenter.to_compact`: Format as compact text for LLM prompt injection.
- `ContextPresenter.to_markdown_grouped`: Markdown grouped by ``doc_type`` (Fase 08).
- `ContextPresenter.to_compact_grouped`: Compact format grouped by ``doc_type`` (Fase 08).
- `ContextPresenter.to_json`: Format as JSON for CI/CD pipeline consumption.

---
Fuente: código de `cortex/context_enricher/presenter.py` (AST + grafo de imports internos). No se usó documentación previa.
