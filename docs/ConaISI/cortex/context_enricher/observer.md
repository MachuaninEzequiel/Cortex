# cortex/context_enricher/observer.py

## Qué tiene adentro

- **Ruta de código:** `cortex/context_enricher/observer.py` (384 líneas).
- **Módulo Python:** `cortex.context_enricher.observer`.
- **Docstring del módulo:** cortex.context_enricher.observer --------------------------------- Observes what the agent is working on and produces a WorkContext.
- **Clases definidas:**
  - `ContextObserver`
    - Observes what the agent is working on and produces a WorkContext.
    - Métodos públicos/especiales: `__init__`, `observe_from_git`, `observe_from_pr`, `observe_from_files`
    - Métodos internos: `_run_git`, `_get_changed_files`, `_get_new_files`, `_get_deleted_files`, `_get_diff_content`, `_extract_imports`, `_extract_functions`, `_extract_classes`, `_extract_keywords`, `_extract_text_keywords`, `_build_context`, `_build_queries`
- **Constantes / símbolos de módulo:** `_IMPORT_PATTERNS`, `_FUNCTION_PATTERNS`, `_CLASS_PATTERNS`, `_ERROR_PATTERNS`, `_ENDPOINT_PATTERNS`

## Para qué sirve

cortex.context_enricher.observer
---------------------------------
Observes what the agent is working on and produces a WorkContext.

Sources:
  - git diff (staged or unstaged changes)
  - PR metadata (title, body, labels, branch)
  - Manual input (explicit files + keywords)

Also extracts: keywords, imports, function/class names, domain,
and generates search queries for the ContextEnricher.

## Relaciones

### Recibe de

- `cortex.context_enricher.domain_detector` (DomainDetector)
- Dependencias externas/stdlib: `re`, `subprocess`, `__future__`, `typing`

### Envía a

- `cortex.context_enricher`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 384.
Docstrings de símbolos públicos:
- `ContextObserver.observe_from_git`: Observe work context from git diff against base branch.
- `ContextObserver.observe_from_pr`: Observe work context from a PR context object.
- `ContextObserver.observe_from_files`: Observe work context from explicit file list.

---
Fuente: código de `cortex/context_enricher/observer.py` (AST + grafo de imports internos). No se usó documentación previa.
