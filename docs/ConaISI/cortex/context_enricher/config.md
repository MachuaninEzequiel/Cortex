# cortex/context_enricher/config.py

## Qué tiene adentro

- **Ruta de código:** `cortex/context_enricher/config.py` (56 líneas).
- **Módulo Python:** `cortex.context_enricher.config`.
- **Docstring del módulo:** cortex.context_enricher.config ------------------------------- Configuration for the Context Enricher: thresholds, budget, boosts, and enabled strategies.
- **Clases definidas:**
  - `ContextEnricherConfig` (BaseModel)
    - Configuration for the Context Enricher pipeline.

## Para qué sirve

cortex.context_enricher.config
-------------------------------
Configuration for the Context Enricher: thresholds, budget, boosts,
and enabled strategies.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `__future__`, `pydantic`

### Envía a

- `cortex.cli.docs_search`
- `cortex.context_enricher.async_enricher`
- `cortex.context_enricher.enricher`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 56.

---
Fuente: código de `cortex/context_enricher/config.py` (AST + grafo de imports internos). No se usó documentación previa.
