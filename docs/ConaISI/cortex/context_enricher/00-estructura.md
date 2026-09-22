# Estructura — `cortex/context_enricher`

## Para qué existe esta carpeta

cortex.context_enricher ----------------------- Proactive context engine for AI agents.

## Árbol interno (código, sin `__pycache__`)

```
context_enricher/
├── __init__.py
├── async_enricher.py
├── budget_resolver.py
├── co_occurrence.py
├── config.py
├── doc_intent.py
├── domain_detector.py
├── enricher.py
├── filters.py
├── observer.py
├── presenter.py
└── telemetry.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/context_enricher/__init__.py` | 34 | cortex.context_enricher ----------------------- Proactive context engine for AI agents. |
| `cortex/context_enricher/async_enricher.py` | 290 | cortex.context_enricher.async_enricher ---------------------------------------- AsyncContextEnricher — parallel multi-strategy search using asyncio. |
| `cortex/context_enricher/budget_resolver.py` | 58 | cortex.context_enricher.budget_resolver — Task-aware retrieval budget. |
| `cortex/context_enricher/co_occurrence.py` | 323 | cortex.context_enricher.co_occurrence --------------------------------- Typed Co-occurrence Graph for semantic file relationships. |
| `cortex/context_enricher/config.py` | 56 | cortex.context_enricher.config ------------------------------- Configuration for the Context Enricher: thresholds, budget, boosts, and enabled strategies. |
| `cortex/context_enricher/doc_intent.py` | 159 | cortex.context_enricher.doc_intent - DocType-aware intent detection. |
| `cortex/context_enricher/domain_detector.py` | 385 | cortex.context_enricher.domain_detector ---------------------------------------- Maps files and keywords to thematic domains (auth, database, api, etc.). |
| `cortex/context_enricher/enricher.py` | 658 | cortex.context_enricher.enricher --------------------------------- Multi-strategy search engine for the Context Enricher. |
| `cortex/context_enricher/filters.py` | 150 | cortex.context_enricher.filters - Structural filters for enrichment. |
| `cortex/context_enricher/observer.py` | 384 | cortex.context_enricher.observer --------------------------------- Observes what the agent is working on and produces a WorkContext. |
| `cortex/context_enricher/presenter.py` | 241 | cortex.context_enricher.presenter ----------------------------------- Formats EnrichedContext for different output targets: - Markdown: human-readable for PR comments - Compact: single-line format for LLM prompt injection - JSON: structured for CI/CD pipelines |
| `cortex/context_enricher/telemetry.py` | 458 | cortex.context_enricher.telemetry - Persistent observer for enrichment events. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.context_enricher.async_enricher`
- `cortex.context_enricher.config`
- `cortex.context_enricher.domain_detector`
- `cortex.context_enricher.enricher`
- `cortex.context_enricher.filters`
- `cortex.context_enricher.observer`
- `cortex.context_enricher.presenter`
- `cortex.documentation.doc_type`
- `cortex.models`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.cli._search_filters`
- `cortex.cli.docs_search`
- `cortex.context_enricher`
- `cortex.context_enricher.async_enricher`
- `cortex.context_enricher.enricher`
- `cortex.context_enricher.observer`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
