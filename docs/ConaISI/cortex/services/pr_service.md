# cortex/services/pr_service.py

## Qué tiene adentro

- **Ruta de código:** `cortex/services/pr_service.py` (179 líneas).
- **Módulo Python:** `cortex.services.pr_service`.
- **Docstring del módulo:** cortex.services.pr_service --------------------------- Domain service for storing PR context and generating fallback documentation.
- **Clases definidas:**
  - `PRService`
    - Handles the PR intake workflow in the DevSecDocOps pipeline.
    - Métodos públicos/especiales: `__init__`, `store_pr_context`, `generate_pr_docs`, `write_pr_docs`

## Para qué sirve

cortex.services.pr_service
---------------------------
Domain service for storing PR context and generating fallback documentation.

Extracted from ``AgentMemory`` to satisfy the Single Responsibility
Principle. This service owns the DevSecDocOps PR workflow:
context enrichment, episodic storage, and fallback doc generation.

Depends on:
- ``cortex.pr_capture.enrich_with_pipeline``   (context enrichment)
- ``cortex.doc_generator.DocGenerator``         (fallback docs)
- ``cortex.episodic.memory_store.EpisodicMemoryStore`` (episodic memory)

## Relaciones

### Recibe de

- `cortex.models` (GeneratedDoc, MemoryEntry, PRContext)
- Dependencias externas/stdlib: `logging`, `__future__`, `pathlib`, `typing`

### Envía a

- `cortex.core`
- `cortex.services`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 179.
Docstrings de símbolos públicos:
- `PRService.store_pr_context`: Enrich a PRContext with pipeline results and store it as a memory.
- `PRService.generate_pr_docs`: Generate fallback documentation from a PRContext.
- `PRService.write_pr_docs`: Write generated PR documents to the vault and index them.

---
Fuente: código de `cortex/services/pr_service.py` (AST + grafo de imports internos). No se usó documentación previa.
