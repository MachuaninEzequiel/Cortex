# cortex/pipeline/stages/documentation.py

## Qué tiene adentro

- **Ruta de código:** `cortex/pipeline/stages/documentation.py` (189 líneas).
- **Módulo Python:** `cortex.pipeline.stages.documentation`.
- **Docstring del módulo:** cortex.pipeline.stages.documentation -------------------------------------- DocumentationStage — doc verification and fallback generation gate.
- **Clases definidas:**
  - `DocumentationStage`
    - Documentation verification and fallback generation stage.
    - Métodos públicos/especiales: `__init__`, `name`, `stage_type`, `block_on_failure`, `execute`
    - Métodos internos: `_store_pr_with_results`, `_verify_docs`, `_index_docs`, `_generate_fallback`

## Para qué sirve

cortex.pipeline.stages.documentation
--------------------------------------
DocumentationStage — doc verification and fallback generation gate.

This is the stage that enforces the DevSecDocOps "done protocol":
work is not done until it is documented.

Flow:
1. Use ``doc_verifier`` to check if agent-written docs exist for this PR.
2. If YES  → index them into the semantic memory. PASS.
3. If NO   → generate a fallback session note. WARN (not block by default).

The stage integrates with ``AgentMemory`` to store the PR context as
an episodic memory regardless of whether docs were found.

## Relaciones

### Recibe de

- `cortex.pipeline.domain.context` (PipelineContext)
- `cortex.pipeline.domain.types` (StageResult, StageStatus, StageType)
- Dependencias externas/stdlib: `logging`, `time`, `__future__`, `typing`

### Envía a

- `cortex.pipeline.stages`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 189.
Docstrings de símbolos públicos:
- `DocumentationStage.execute`: Verify documentation and generate fallback if needed.

---
Fuente: código de `cortex/pipeline/stages/documentation.py` (AST + grafo de imports internos). No se usó documentación previa.
