"""cortex.ci — Phase 07 CI plugin (Pluggable Middle).

Provider-agnostic validation of pull requests against the matching
Cortex Session + spec. Exposes:

* :func:`validate_pull_request` — top-level entry point used by the
  CLI (``cortex ci validate-pr``).
* :class:`ValidationResult` — typed output (also serialised to JSON for
  workflow consumers).
* :func:`render_pr_comment` — Markdown formatter for the Level 2 PR
  comment workflow.

The CLI lives in :mod:`cortex.cli.ci`; this package holds the pure
logic.
"""

from __future__ import annotations

from cortex.ci.markdown_formatter import render_pr_comment
from cortex.ci.result import ScopeDriftFinding, ValidationInput, ValidationResult
from cortex.ci.validator import CiValidator, validate_pull_request

__all__ = [
    "CiValidator",
    "ScopeDriftFinding",
    "ValidationInput",
    "ValidationResult",
    "render_pr_comment",
    "validate_pull_request",
]
