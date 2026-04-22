"""
cortex.pipeline.runners
------------------------
CI/CD provider adapters for the Cortex pipeline.

Runners translate a list of PipelineStage definitions into
provider-specific configuration (YAML workflows, API calls, etc.).

Available runners
-----------------
- ``GitHubActionsRunner`` → generates GitHub Actions workflow YAML
"""

from cortex.pipeline.runners.github import GitHubActionsRunner

__all__ = ["GitHubActionsRunner"]
