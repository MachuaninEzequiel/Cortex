"""
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
"""

from cortex.pipeline.stages.documentation import DocumentationStage
from cortex.pipeline.stages.lint import LintStage
from cortex.pipeline.stages.security import SecurityStage
from cortex.pipeline.stages.test import TestStage

__all__ = [
    "SecurityStage",
    "LintStage",
    "TestStage",
    "DocumentationStage",
]
