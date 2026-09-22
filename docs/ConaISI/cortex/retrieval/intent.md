# cortex/retrieval/intent.py

## Qué tiene adentro

- **Ruta de código:** `cortex/retrieval/intent.py` (175 líneas).
- **Módulo Python:** `cortex.retrieval.intent`.
- **Docstring del módulo:** cortex.retrieval.intent ------------------------ Query intent detector for adaptive RRF weight computation.
- **Clases definidas:**
  - `QueryIntent` (Enum)
    - Semantic classification of a search query.
  - `IntentResult`
    - Result of intent detection for a single query.
  - `QueryIntentDetector`
    - Detects the intent of a search query to enable adaptive RRF weighting.
    - Métodos públicos/especiales: `__init__`, `detect`
- **Constantes / símbolos de módulo:** `_EPISODIC_SIGNALS`, `_SEMANTIC_SIGNALS`, `_WEIGHTS`

## Para qué sirve

cortex.retrieval.intent
------------------------
Query intent detector for adaptive RRF weight computation.

Analyzes a natural-language query and returns an IntentResult
that the HybridSearch uses to adaptively weight episodic vs.
semantic sources before fusing with RRF.

Intent taxonomy
---------------
EPISODIC    → Queries about past events, decisions, bugs, fixes.
              Examples: "what did we decide", "last time this broke",
                        "fix login token", "PR #42"
SEMANTIC    → Queries about concepts, architecture, runbooks, specs.
              Examples: "how does auth work", "architecture diagram",
                        "deployment runbook", "API contract"
MIXED       → Ambiguous queries that benefit from both sources equally.
              Examples: "authentication", "token refresh"

Weight mapping (episodic_weight, semantic_weight)
-------------------------------------------------
EPISODIC → (2.0, 0.6)  ← pull hard from episodic, light semantic
SEMANTIC → (0.6, 2.0)  ← pull hard from semantic vault
MIXED    → (1.0, 1.0)  ← balanced (original behavior preserved)

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `re`, `__future__`, `dataclasses`, `enum`

### Envía a

- `cortex.retrieval`
- `cortex.retrieval.hybrid_search`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 175.
Docstrings de símbolos públicos:
- `QueryIntentDetector.detect`: Classify the intent of a query and return adaptive weights.

---
Fuente: código de `cortex/retrieval/intent.py` (AST + grafo de imports internos). No se usó documentación previa.
