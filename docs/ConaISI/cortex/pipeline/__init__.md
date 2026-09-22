# cortex/pipeline/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/pipeline/__init__.py` (57 líneas).
- **Módulo Python:** `cortex.pipeline`.
- **Docstring del módulo:** cortex.pipeline --------------- DevSecDocOps Pipeline — formal Python abstraction for CI/CD stages.
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.pipeline
---------------
DevSecDocOps Pipeline — formal Python abstraction for CI/CD stages.

This module replaces the implicit, script-based pipeline with a
typed, testable, provider-agnostic architecture.

Structure
---------
- ``domain``      → Pure types: StageResult, StageType, PipelineContext,
                    PipelineStage (Protocol). No I/O, no side effects.
- ``stages``      → Concrete stage implementations (lint, test, security,
                    documentation). Pluggable via Protocol.
- ``runners``     → CI/CD provider adapters that translate a Pipeline
                    definition into provider-specific config (YAML, API calls).
- ``orchestrator``→ Executes stages in order, collects results, enforces gates.

Quick start
-----------
    from cortex.pipeline import PipelineOrchestrator, PipelineContext
    from cortex.pipeline.stages import LintStage, TestStage, SecurityStage, DocumentationStage

    ctx = PipelineContext.from_pr_context(pr_ctx, vault_path="vault")
    orchestrator = PipelineOrchestrator(stages=[
        SecurityStage(),
        LintStage(),
        TestStage(min_coverage=85),
        DocumentationStage(memory=agent_memory),
    ])
    report = orchestrator.run(ctx)
    print(report.summary())

## Relaciones

### Recibe de

- `cortex.pipeline.domain.context` (PipelineContext)
- `cortex.pipeline.domain.protocols` (PipelineStage)
- `cortex.pipeline.domain.types` (PipelineReport, StageResult, StageStatus, StageType)
- `cortex.pipeline.orchestrator` (PipelineOrchestrator)

### Envía a

- `cortex.__init__`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 57.
Reexportes observados:
- cortex.pipeline.domain.context: PipelineContext
- cortex.pipeline.domain.protocols: PipelineStage
- cortex.pipeline.domain.types: PipelineReport, StageResult, StageStatus, StageType
- cortex.pipeline.orchestrator: PipelineOrchestrator

---
Fuente: código de `cortex/pipeline/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
