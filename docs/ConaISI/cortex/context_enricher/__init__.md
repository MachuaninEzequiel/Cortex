# cortex/context_enricher/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/context_enricher/__init__.py` (34 líneas).
- **Módulo Python:** `cortex.context_enricher`.
- **Docstring del módulo:** cortex.context_enricher ----------------------- Proactive context engine for AI agents.
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.context_enricher
-----------------------
Proactive context engine for AI agents.

Observes what the agent is working on, searches the project's memory
across multiple strategies, deduplicates, ranks, and injects relevant
context automatically.

Components
----------
ContextObserver      → Extracts work context from git/PR/manual input
DomainDetector       → Maps files/keywords to thematic domains
ContextEnricher      → Multi-strategy search + dedup + rank (sequential)
AsyncContextEnricher → Same as above, strategies run in parallel (faster)
ContextPresenter     → Formats context for CLI, LLM prompt, or JSON

## Relaciones

### Recibe de

- `cortex.context_enricher.async_enricher` (AsyncContextEnricher)
- `cortex.context_enricher.domain_detector` (DomainDetector, DomainMatch)
- `cortex.context_enricher.enricher` (ContextEnricher, ContextEnricherConfig)
- `cortex.context_enricher.observer` (ContextObserver)
- `cortex.context_enricher.presenter` (ContextPresenter)

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 34.
Reexportes observados:
- cortex.context_enricher.async_enricher: AsyncContextEnricher
- cortex.context_enricher.domain_detector: DomainDetector, DomainMatch
- cortex.context_enricher.enricher: ContextEnricher, ContextEnricherConfig
- cortex.context_enricher.observer: ContextObserver
- cortex.context_enricher.presenter: ContextPresenter

---
Fuente: código de `cortex/context_enricher/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
