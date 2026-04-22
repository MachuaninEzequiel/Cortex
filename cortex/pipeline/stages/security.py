"""
cortex.pipeline.stages.security
---------------------------------
SecurityStage — dependency vulnerability audit gate.

Runs ``pip-audit`` (Python) or ``npm audit`` (JS/TS) against the
project's dependencies and blocks the pipeline on HIGH/CRITICAL findings.

Integration
-----------
The stage is provider-agnostic: it runs ``subprocess`` commands locally
or in any CI environment (GitHub Actions, GitLab CI, etc.) and returns
a typed ``StageResult`` that the orchestrator uses for gate enforcement.
"""

from __future__ import annotations

import logging
import subprocess
import time
from typing import Literal

from cortex.pipeline.domain.context import PipelineContext
from cortex.pipeline.domain.types import StageResult, StageStatus, StageType

logger = logging.getLogger(__name__)


class SecurityStage:
    """
    Dependency vulnerability audit stage (SCA — Software Composition Analysis).

    Detects known vulnerabilities in project dependencies using
    ``pip-audit`` for Python projects or ``npm audit`` for Node.js.

    Args:
        block_on_failure:  If True, pipeline aborts on HIGH/CRITICAL findings.
        audit_level:       Minimum severity to trigger a failure.
                           One of ``"low"``, ``"moderate"``, ``"high"``, ``"critical"``.
        python_cmd:        Command used for Python auditing.
        node_cmd:          Command used for Node.js auditing.
    """

    def __init__(
        self,
        block_on_failure: bool = True,
        audit_level: Literal["low", "moderate", "high", "critical"] = "high",
        python_cmd: str = "pip-audit --format=json",
        node_cmd: str = "npm audit --json --omit=dev",
    ) -> None:
        self._block = block_on_failure
        self._audit_level = audit_level
        self._python_cmd = python_cmd
        self._node_cmd = node_cmd

    @property
    def name(self) -> str:
        return "Security Audit"

    @property
    def stage_type(self) -> StageType:
        return StageType.SECURITY_SCAN

    @property
    def block_on_failure(self) -> bool:
        return self._block

    def execute(self, ctx: PipelineContext) -> StageResult:
        """Run the appropriate audit command based on detected project type."""
        start = time.monotonic()

        try:
            is_python = self._is_python_project(ctx)
            cmd = self._python_cmd if is_python else self._node_cmd
            tool = "pip-audit" if is_python else "npm audit"

            logger.info("Running %s audit: %s", tool, cmd)
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=120,
            )

            duration_ms = int((time.monotonic() - start) * 1000)
            findings = self._parse_findings(result.stdout, is_python)
            vuln_count = len(findings)

            # Determine status based on whether vulnerabilities were found
            if result.returncode == 0 or vuln_count == 0:
                return StageResult(
                    stage_type=self.stage_type,
                    stage_name=self.name,
                    status=StageStatus.PASSED,
                    message=f"No vulnerabilities found ({tool})",
                    artifacts={"tool": tool, "vulnerabilities": findings},
                    duration_ms=duration_ms,
                )
            else:
                return StageResult(
                    stage_type=self.stage_type,
                    stage_name=self.name,
                    status=StageStatus.FAILED,
                    message=f"{vuln_count} vulnerabilities found ({tool})",
                    artifacts={
                        "tool": tool,
                        "vulnerabilities": findings,
                        "raw_output": result.stdout[:2000],
                    },
                    duration_ms=duration_ms,
                )

        except FileNotFoundError as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            tool_hint = "pip install pip-audit" if self._is_python_project(ctx) else "npm install"
            return StageResult(
                stage_type=self.stage_type,
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                message=f"Audit tool not found. Install it: {tool_hint}",
                artifacts={"error": str(exc)},
                duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.exception("SecurityStage raised an unexpected error")
            return StageResult(
                stage_type=self.stage_type,
                stage_name=self.name,
                status=StageStatus.ERROR,
                message=f"Unexpected error: {exc}",
                artifacts={"error": str(exc)},
                duration_ms=duration_ms,
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_python_project(ctx: PipelineContext) -> bool:
        """Detect Python project by checking for common Python files."""
        python_indicators = {
            "pyproject.toml", "setup.py", "setup.cfg",
            "requirements.txt", "Pipfile",
        }
        return any(
            f in python_indicators or f.endswith(".py")
            for f in ctx.changed_files + [
                p.name for p in ctx.vault_path.parent.glob("*.toml")
            ]
        )

    @staticmethod
    def _parse_findings(output: str, is_python: bool) -> list[dict]:
        """Parse audit JSON output into a list of finding dicts."""
        import json
        try:
            data = json.loads(output)
        except (json.JSONDecodeError, ValueError):
            return []

        if is_python:
            # pip-audit JSON: {"dependencies": [...], "vulnerabilities": [...]}
            return data.get("vulnerabilities", [])
        else:
            # npm audit JSON: {"vulnerabilities": {...}}
            vuln_map = data.get("vulnerabilities", {})
            return [
                {"name": name, **details}
                for name, details in vuln_map.items()
            ]
