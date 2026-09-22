# cortex/context_enricher/telemetry.py

## Qué tiene adentro

- **Ruta de código:** `cortex/context_enricher/telemetry.py` (458 líneas).
- **Módulo Python:** `cortex.context_enricher.telemetry`.
- **Docstring del módulo:** cortex.context_enricher.telemetry - Persistent observer for enrichment events.
- **Clases definidas:**
  - `EnrichmentEvent`
    - A single enrichment invocation.
  - `CitationEvent`
    - An item that was actually cited by the agent.
  - `PersistentObserver`
    - Append-only JSONL log of enrichment and citation events.
    - Métodos públicos/especiales: `__init__`, `enabled`, `path`, `record_enrichment`, `record_citation`, `iter_events`, `events_for_run`, `aggregate`
    - Métodos internos: `_append`, `_rotate_if_needed`
- **Funciones de módulo:**
  - `detect_citations(body, items_offered)` — Detect which offered items were cited in the session body.
  - `_parse_ts(value)`
  - `_percentile(sorted_values, pct)`
  - `make_observer(workspace_layout)` — Create a ``PersistentObserver`` from a ``WorkspaceLayout`` or path.
- **Constantes / símbolos de módulo:** `_WIKI_LINK_RE`, `_MD_LINK_RE`, `__all__`

## Para qué sirve

cortex.context_enricher.telemetry - Persistent observer for enrichment events.

Implements the Mecanismo 1 telemetry of the canonical-documentation initiative:
every call to ``ContextEnricher.enrich()`` produces an ``EnrichmentEvent``
appended to ``.cortex/enrichment-events.jsonl``. When the agent later cites an
item (via wiki-link or markdown link inside the session body) a ``CitationEvent``
is appended to the same file.

The session writer reads recent events to populate the ``cortex_telemetry``
frontmatter block on the session note.

The observer is non-blocking: persistence failures are logged but never abort
the enrichment pipeline.

This module is opt-in. ``ContextEnricher`` accepts ``observer=None`` and
behaves exactly as before when no observer is attached.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `json`, `logging`, `re`, `statistics`, `uuid`, `__future__`, `collections`, `dataclasses`, `datetime`, `pathlib`, `typing`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 458.
Docstrings de símbolos públicos:
- `PersistentObserver.record_enrichment`: Record an enrichment event. Returns the new ``run_id``.
- `PersistentObserver.record_citation`: Record that the agent cited an item from ``run_id``.
- `PersistentObserver.iter_events`: Load all events from disk (vivo + generación rotada, en orden).
- `PersistentObserver.events_for_run`: Return ``{"enrichment": <event>, "citations": [<event>, ...]}`` for a run.
- `PersistentObserver.aggregate`: Aggregate events to produce a memory-report payload.
- `detect_citations`: Detect which offered items were cited in the session body.
- `make_observer`: Create a ``PersistentObserver`` from a ``WorkspaceLayout`` or path.

---
Fuente: código de `cortex/context_enricher/telemetry.py` (AST + grafo de imports internos). No se usó documentación previa.
