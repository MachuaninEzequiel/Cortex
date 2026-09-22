# cortex/enterprise/promotion_models.py

## Qué tiene adentro

- **Ruta de código:** `cortex/enterprise/promotion_models.py` (75 líneas).
- **Módulo Python:** `cortex.enterprise.promotion_models`.
- **Clases definidas:**
  - `PromotionIssue` (BaseModel)
  - `PromotionCandidate` (BaseModel)
  - `PromotionDecision` (BaseModel)
  - `PromotionRecordEvent` (BaseModel)
  - `PromotionRecord` (BaseModel)
    - Append-only record describing the lifecycle of one promotable document.
    - Métodos públicos/especiales: `touch`

## Para qué sirve

Define PromotionIssue, PromotionCandidate, PromotionDecision, PromotionRecordEvent, PromotionRecord. No hay docstring de módulo; el propósito se infiere de las clases y métodos listados.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `__future__`, `datetime`, `typing`, `pydantic`

### Envía a

- `cortex.enterprise.knowledge_promotion`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 75.

---
Fuente: código de `cortex/enterprise/promotion_models.py` (AST + grafo de imports internos). No se usó documentación previa.
