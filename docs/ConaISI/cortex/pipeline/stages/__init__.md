# cortex/pipeline/stages/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/pipeline/stages/__init__.py` (28 líneas).
- **Módulo Python:** `cortex.pipeline.stages`.
- **Docstring del módulo:** cortex.pipeline.stages ----------------------- Concrete implementations of PipelineStage for each DevSecDocOps gate.
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.pipeline.stages
-----------------------
Concrete implementations of PipelineStage for each DevSecDocOps gate.

All stages satisfy the PipelineStage Protocol structurally — no
inheritance from a base class is needed or used.

Available stages
----------------
- ``SecurityStage``      → dependency audit (pip-audit / npm-audit)
- ``LintStage``          → static analysis (ruff, eslint, etc.)
- ``TestStage``          → test suite + coverage enforcement
- ``DocumentationStage`` → doc verification + fallback generation

## Relaciones

### Recibe de

- `cortex.pipeline.stages.documentation` (DocumentationStage)
- `cortex.pipeline.stages.lint` (LintStage)
- `cortex.pipeline.stages.security` (SecurityStage)
- `cortex.pipeline.stages.test` (TestStage)

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 28.
Reexportes observados:
- cortex.pipeline.stages.documentation: DocumentationStage
- cortex.pipeline.stages.lint: LintStage
- cortex.pipeline.stages.security: SecurityStage
- cortex.pipeline.stages.test: TestStage

---
Fuente: código de `cortex/pipeline/stages/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
