"""
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
"""

from cortex.pipeline.domain.context import PipelineContext
from cortex.pipeline.domain.protocols import PipelineStage
from cortex.pipeline.domain.types import (
    PipelineReport,
    StageResult,
    StageStatus,
    StageType,
)
from cortex.pipeline.orchestrator import PipelineOrchestrator

__all__ = [
    # Domain types
    "StageType",
    "StageStatus",
    "StageResult",
    "PipelineReport",
    "PipelineContext",
    # Protocol
    "PipelineStage",
    # Orchestrator
    "PipelineOrchestrator",
]
