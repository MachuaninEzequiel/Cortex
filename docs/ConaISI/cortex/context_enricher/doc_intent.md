# cortex/context_enricher/doc_intent.py

## Qué tiene adentro

- **Ruta de código:** `cortex/context_enricher/doc_intent.py` (159 líneas).
- **Módulo Python:** `cortex.context_enricher.doc_intent`.
- **Docstring del módulo:** cortex.context_enricher.doc_intent - DocType-aware intent detection.
- **Clases definidas:**
  - `DocIntent` (str, Enum)
    - Intent label used to boost specific DocTypes during retrieval.
  - `DocIntentResult`
  - `DocIntentDetector`
    - Classifies a query into a ``DocIntent`` via lexicon matching.
    - Métodos públicos/especiales: `detect`
- **Constantes / símbolos de módulo:** `_DOC_PATTERNS`, `__all__`

## Para qué sirve

cortex.context_enricher.doc_intent - DocType-aware intent detection.

Complements ``cortex.retrieval.intent.QueryIntent`` (EPISODIC/SEMANTIC/MIXED,
which controls RRF weights) with a finer-grained ``DocIntent`` used to boost
specific DocTypes during retrieval.

Example:
    A query like "how do I rollback?" maps to ``DocIntent.RUNBOOK`` which
    boosts ``RUNBOOK`` documents 2.5x via ``RouteSpec.retrieval_boost_per_intent``.

The two layers are orthogonal: ``QueryIntent`` decides episodic-vs-semantic
weights for RRF fusion; ``DocIntent`` decides per-doc_type score multipliers
within the semantic vault.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `re`, `__future__`, `dataclasses`, `enum`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 159.

---
Fuente: código de `cortex/context_enricher/doc_intent.py` (AST + grafo de imports internos). No se usó documentación previa.
