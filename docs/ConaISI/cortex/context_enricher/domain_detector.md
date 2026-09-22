# cortex/context_enricher/domain_detector.py

## Qué tiene adentro

- **Ruta de código:** `cortex/context_enricher/domain_detector.py` (385 líneas).
- **Módulo Python:** `cortex.context_enricher.domain_detector`.
- **Docstring del módulo:** cortex.context_enricher.domain_detector ---------------------------------------- Maps files and keywords to thematic domains (auth, database, api, etc.).
- **Clases definidas:**
  - `DomainMatch`
    - Result of domain detection.
  - `DomainDetector`
    - Detects the thematic domain from file paths and keywords.
    - Métodos públicos/especiales: `__init__`, `detect`
    - Métodos internos: `_initialize_embedding_fallback`, `_embedding_fallback`
- **Constantes / símbolos de módulo:** `DOMAIN_RULES`, `_FILE_WEIGHT`, `_KEYWORD_WEIGHT`

## Para qué sirve

cortex.context_enricher.domain_detector
----------------------------------------
Maps files and keywords to thematic domains (auth, database, api, etc.).

Uses pattern matching with weighted scoring:
  - File patterns (weight 0.6): filename/path contains domain keywords
  - Keyword patterns (weight 0.4): content/code contains domain keywords

Returns the best-matching domain only if confidence > threshold.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `__future__`, `dataclasses`, `typing`

### Envía a

- `cortex.context_enricher`
- `cortex.context_enricher.observer`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 385.
Docstrings de símbolos públicos:
- `DomainDetector.detect`: Detect the thematic domain from files and keywords.

---
Fuente: código de `cortex/context_enricher/domain_detector.py` (AST + grafo de imports internos). No se usó documentación previa.
