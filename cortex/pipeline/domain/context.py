"""
cortex.pipeline.domain.context
--------------------------------
PipelineContext — the shared execution context passed to every stage.

This is the single source of truth for a pipeline run. Every stage
reads from it (changed files, PR metadata, config) and may write
results back into the shared ``stage_outputs`` dict.

Design decisions:
- Uses a regular dataclass (not frozen) because the orchestrator
  populates ``stage_outputs`` as stages complete.
- Factory methods make construction from different sources explicit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.models import PRContext


@dataclass
class PipelineContext:
    """
    Shared execution context for all pipeline stages.

    Attributes:
        vault_path:      Path to the Obsidian vault.
        changed_files:   Files modified in this PR / commit.
        pr_number:       Pull request number (0 if not a PR run).
        pr_title:        Pull request title.
        pr_author:       GitHub login of the PR author.
        source_branch:   Feature branch name.
        target_branch:   Target branch (typically "main").
        commit_sha:      Full commit SHA.
        labels:          PR labels (used by gate rules).
        config:          Pipeline config dict from config.yaml.
        stage_outputs:   Mutable dict populated by stages as they run.
                         Use this to pass data between stages without
                         creating direct dependencies.
    """
    vault_path:    Path
    changed_files: list[str]       = field(default_factory=list)
    pr_number:     int             = 0
    pr_title:      str             = ""
    pr_author:     str             = ""
    source_branch: str             = ""
    target_branch: str             = "main"
    commit_sha:    str             = ""
    labels:        list[str]       = field(default_factory=list)
    config:        dict[str, Any]  = field(default_factory=dict)
    stage_outputs: dict[str, Any]  = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    @classmethod
    def from_pr_context(
        cls,
        pr_ctx: PRContext,
        *,
        vault_path: str | Path = "vault",
        config: dict[str, Any] | None = None,
    ) -> PipelineContext:
        """
        Build a PipelineContext from an existing PRContext model.

        Args:
            pr_ctx:     Captured PR context (from pr_capture.py).
            vault_path: Path to the Obsidian vault.
            config:     Pipeline config section from config.yaml.

        Returns:
            PipelineContext ready for orchestrator consumption.
        """
        return cls(
            vault_path=Path(vault_path),
            changed_files=list(pr_ctx.files_changed),
            pr_number=pr_ctx.pr_number,
            pr_title=pr_ctx.title,
            pr_author=pr_ctx.author,
            source_branch=pr_ctx.source_branch,
            target_branch=pr_ctx.target_branch,
            commit_sha=pr_ctx.commit_sha,
            labels=list(pr_ctx.labels),
            config=config or {},
        )

    @classmethod
    def from_env(
        cls,
        *,
        vault_path: str | Path = "vault",
        config: dict[str, Any] | None = None,
    ) -> PipelineContext:
        """
        Build a PipelineContext from GitHub Actions environment variables.

        Useful for running the pipeline directly in CI without pre-capturing
        a PRContext JSON file.

        Args:
            vault_path: Path to the Obsidian vault.
            config:     Pipeline config section from config.yaml.

        Returns:
            PipelineContext populated from GITHUB_* env vars.
        """
        import os
        from cortex.pr_capture import _get_files_changed, _get_diff_summary  # type: ignore

        pr_number    = int(os.getenv("PR_NUMBER", "0"))
        pr_title     = os.getenv("PR_TITLE", os.getenv("GITHUB_EVENT_PR_TITLE", ""))
        pr_author    = os.getenv("PR_AUTHOR", os.getenv("GITHUB_ACTOR", "unknown"))
        source_branch = os.getenv("PR_BRANCH", os.getenv("GITHUB_HEAD_REF", ""))
        target_branch = os.getenv("TARGET_BRANCH", os.getenv("GITHUB_BASE_REF", "main"))
        commit_sha   = os.getenv("PR_COMMIT", os.getenv("GITHUB_SHA", ""))
        labels_raw   = os.getenv("PR_LABELS", "")
        labels       = [l.strip() for l in labels_raw.split(",") if l.strip()]
        changed_files = _get_files_changed(target_branch, commit_sha)

        return cls(
            vault_path=Path(vault_path),
            changed_files=changed_files,
            pr_number=pr_number,
            pr_title=pr_title,
            pr_author=pr_author,
            source_branch=source_branch,
            target_branch=target_branch,
            commit_sha=commit_sha,
            labels=labels,
            config=config or {},
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def get_stage_output(self, stage_name: str, key: str, default: Any = None) -> Any:
        """
        Retrieve a value written by a previous stage.

        Args:
            stage_name: Name of the stage that wrote the value.
            key:        Key within that stage's output dict.
            default:    Value to return if not found.
        """
        return self.stage_outputs.get(stage_name, {}).get(key, default)

    def set_stage_output(self, stage_name: str, key: str, value: Any) -> None:
        """
        Write a value to the shared inter-stage communication dict.

        Args:
            stage_name: Name of the current stage (use ``stage.name``).
            key:        Key to store under.
            value:      Value to store.
        """
        if stage_name not in self.stage_outputs:
            self.stage_outputs[stage_name] = {}
        self.stage_outputs[stage_name][key] = value
