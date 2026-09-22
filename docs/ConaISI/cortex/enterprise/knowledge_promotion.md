# cortex/enterprise/knowledge_promotion.py

## Qué tiene adentro

- **Ruta de código:** `cortex/enterprise/knowledge_promotion.py` (339 líneas).
- **Módulo Python:** `cortex.enterprise.knowledge_promotion`.
- **Clases definidas:**
  - `PromotionPaths`
  - `PromotionRepository`
    - Métodos públicos/especiales: `__init__`, `iter_records`, `load_latest_by_origin_id`, `append`
  - `PromotionRulesEngine`
    - Métodos públicos/especiales: `__init__`, `is_promotable`
  - `KnowledgePromotionService`
    - Métodos públicos/especiales: `__init__`, `from_project_root`, `discover_candidates`, `review`, `plan_promotion`, `apply_promotion`
    - Métodos internos: `_project_slug`, `_origin_id`, `_dest_rel_path`
- **Funciones de módulo:**
  - `_utc_now()`
  - `_split_frontmatter(raw)`
  - `_upsert_frontmatter(raw, updates)`
  - `_normalized_markdown_fingerprint(raw)`
  - `_doc_type_from_rel_path(rel_path)`
- **Constantes / símbolos de módulo:** `_FRONTMATTER_RE`

## Para qué sirve

Define PromotionPaths, PromotionRepository, PromotionRulesEngine, KnowledgePromotionService. No hay docstring de módulo; el propósito se infiere de las clases y métodos listados.

## Relaciones

### Recibe de

- `cortex.doc_validator` (DocValidator)
- `cortex.enterprise.config` (load_enterprise_config)
- `cortex.enterprise.promotion_models` (PromotionCandidate, PromotionDecision, PromotionIssue, PromotionRecord, PromotionRecordEvent)
- `cortex.runtime_context` (slugify)
- `cortex.workspace.layout` (WorkspaceLayout)
- Dependencias externas/stdlib: `hashlib`, `json`, `re`, `yaml`, `__future__`, `collections.abc`, `dataclasses`, `datetime`, `pathlib`, `typing`

### Envía a

- `cortex.enterprise.reporting`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 339.
Docstrings de símbolos públicos:
- `KnowledgePromotionService.from_project_root`: Create a KnowledgePromotionService from a project root.

---
Fuente: código de `cortex/enterprise/knowledge_promotion.py` (AST + grafo de imports internos). No se usó documentación previa.
