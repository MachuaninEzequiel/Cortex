"""
cortex.pipeline.runners.github
--------------------------------
GitHubActionsRunner — generates GitHub Actions workflow YAML from a
pipeline stage configuration.

This is a pure generator: it takes a list of stage types and a
pipeline config dict, and produces valid YAML that can be written
to ``.github/workflows/``. No I/O of its own.

Design
------
The runner knows the GitHub Actions primitives (jobs, steps, secrets,
caching) but knows nothing about business logic. It maps StageType
to the appropriate shell commands via the project context.

Extensibility
-------------
To add a new CI provider (GitLab CI, Azure DevOps, Jenkins):
1. Create ``cortex/pipeline/runners/gitlab.py`` with a ``GitLabCIRunner``.
2. Implement ``generate_workflow(stages, config) -> str``.
3. Register it in ``runners/__init__.py``.
No changes needed anywhere else.
"""

from __future__ import annotations

from cortex.pipeline.domain.types import StageType


class GitHubActionsRunner:
    """
    Generates GitHub Actions workflow YAML for the DevSecDocOps pipeline.

    The generated workflow implements the same stages as the Python
    orchestrator but natively in GitHub Actions, using Cortex CLI
    commands to bridge back into the Python domain layer.

    Args:
        python_version: Python version to use in the workflow.
        runs_on:        GitHub Actions runner image.
        branches:       Branches that trigger the PR workflow.
    """

    def __init__(
        self,
        python_version: str = "3.11",
        runs_on: str = "ubuntu-latest",
        branches: list[str] | None = None,
    ) -> None:
        self._python_version = python_version
        self._runs_on = runs_on
        self._branches = branches or ["main", "master"]

    def generate_pr_workflow(
        self,
        stages: list[StageType],
        *,
        install_cmd: str = "pip install -e '.[dev]'",
        test_cmd: str = "pytest --cov=. --cov-report=term-missing -q",
        lint_cmd: str = "ruff check .",
        audit_cmd: str = "pip-audit || true",
        min_coverage: int = 0,
    ) -> str:
        """
        Generate a complete GitHub Actions workflow YAML for PR validation.

        Args:
            stages:       List of StageType values to include. Order matters
                          for gate enforcement.
            install_cmd:  Shell command to install project dependencies.
            test_cmd:     Shell command to run the test suite.
            lint_cmd:     Shell command to run the linter.
            audit_cmd:    Shell command to audit dependencies.
            min_coverage: Minimum coverage %. 0 = no enforcement.

        Returns:
            Complete YAML string ready to write to
            ``.github/workflows/cortex-ci.yml``.
        """
        branch_list = "\n".join(f"      - '{b}'" for b in self._branches)
        steps = self._build_steps(
            stages,
            install_cmd=install_cmd,
            test_cmd=test_cmd,
            lint_cmd=lint_cmd,
            audit_cmd=audit_cmd,
            min_coverage=min_coverage,
        )

        return f"""\
name: Cortex DevSecDocOps — PR Validation

on:
  pull_request:
    branches:
{branch_list}
    types: [opened, reopened, synchronize]

permissions:
  contents: write
  pull-requests: write
  issues: write

jobs:
  cortex-pipeline:
    name: DevSecDocOps Gate
    runs-on: {self._runs_on}

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Python {self._python_version}
        uses: actions/setup-python@v5
        with:
          python-version: '{self._python_version}'

      - name: Restore Cortex Memory Cache
        id: cache-restore
        uses: actions/cache/restore@v4
        with:
          path: .memory/chroma
          key: cortex-memory-${{{{ github.run_id }}}}
          restore-keys: |
            cortex-memory-

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          {install_cmd}

      - name: Cortex — Capture PR Context
        id: capture
        run: |
          cortex pr-context capture \\
            --title "${{{{ github.event.pull_request.title }}}}" \\
            --body "${{{{ github.event.pull_request.body || '' }}}}" \\
            --author "${{{{ github.event.pull_request.user.login }}}}" \\
            --branch "${{{{ github.event.pull_request.head.ref }}}}" \\
            --commit "${{{{ github.event.pull_request.head.sha }}}}" \\
            --pr-number "${{{{ github.event.pull_request.number }}}}" \\
            --target-branch "${{{{ github.event.pull_request.base.ref }}}}" \\
            --labels "${{{{ join(github.event.pull_request.labels.*.name, ',') }}}}" \\
            --output .pr-context.json

{steps}

      - name: Cortex — Search Past Context
        if: always()
        run: |
          cortex pr-context search \\
            --context-file .pr-context.json \\
            --output .past-context.json
        continue-on-error: true

      - name: Cortex — Sync Vault
        if: always()
        run: cortex sync-vault

      - name: Save Cortex Memory Cache
        if: always()
        uses: actions/cache/save@v4
        with:
          path: .memory/chroma
          key: cortex-memory-${{{{ github.run_id }}}}

      - name: Auto-commit documentation
        if: always()
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "docs(cortex): auto-generate DevSecDocOps session docs"
          file_pattern: "vault/**"

      - name: Upload Cortex Artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: cortex-context-${{{{ github.event.pull_request.number }}}}-${{{{ github.run_id }}}}
          path: |
            .pr-context.json
            .past-context.json
          retention-days: 14
"""

    # ------------------------------------------------------------------
    # Private — step builder
    # ------------------------------------------------------------------

    def _build_steps(
        self,
        stages: list[StageType],
        *,
        install_cmd: str,
        test_cmd: str,
        lint_cmd: str,
        audit_cmd: str,
        min_coverage: int,
    ) -> str:
        """Build the YAML step blocks for each requested StageType."""
        blocks: list[str] = []

        for stage_type in stages:
            if stage_type == StageType.SECURITY_SCAN:
                blocks.append(self._step_security(audit_cmd))
            elif stage_type == StageType.LINT:
                blocks.append(self._step_lint(lint_cmd))
            elif stage_type == StageType.TEST:
                blocks.append(self._step_test(test_cmd, min_coverage))
            elif stage_type == StageType.DOCUMENTATION:
                blocks.append(self._step_documentation())

        return "\n".join(blocks)

    @staticmethod
    def _step_security(audit_cmd: str) -> str:
        return f"""\
      # ── Security Gate ────────────────────────────────────────────
      - name: Security Audit
        id: security
        run: {audit_cmd}
        continue-on-error: true

      - name: Cortex — Store Security Result
        if: always()
        run: |
          cortex pr-context store \\
            --context-file .pr-context.json \\
            --audit-result "${{{{ steps.security.outcome }}}}"

      - name: Check Security Gate
        if: steps.security.outcome != 'success'
        run: |
          echo "❌ Security audit failed. Review vulnerabilities before merging."
          exit 1
"""

    @staticmethod
    def _step_lint(lint_cmd: str) -> str:
        return f"""\
      # ── Lint Gate ────────────────────────────────────────────────
      - name: Lint
        id: lint
        run: {lint_cmd}
        continue-on-error: true

      - name: Cortex — Store Lint Result
        if: always()
        run: |
          cortex pr-context store \\
            --context-file .pr-context.json \\
            --lint-result "${{{{ steps.lint.outcome }}}}"

      - name: Check Lint Gate
        if: steps.lint.outcome != 'success'
        run: |
          echo "❌ Lint check failed. Fix errors before merging."
          exit 1
"""

    @staticmethod
    def _step_test(test_cmd: str, min_coverage: int) -> str:
        coverage_check = ""
        if min_coverage > 0:
            coverage_check = f"""
      - name: Check Coverage Gate
        if: steps.tests.outcome == 'success'
        run: |
          COVERAGE=$(python -c "
          import re, sys
          output = open('/tmp/test-output.txt').read()
          m = re.search(r'TOTAL.*?(\\d+)%', output)
          print(m.group(1) if m else '0')
          " 2>/dev/null || echo "0")
          if [ "$COVERAGE" -lt "{min_coverage}" ]; then
            echo "❌ Coverage $COVERAGE% is below minimum {min_coverage}%"
            exit 1
          fi
          echo "✅ Coverage $COVERAGE% meets minimum {min_coverage}%"
"""
        return f"""\
      # ── Test Gate ────────────────────────────────────────────────
      - name: Tests
        id: tests
        run: {test_cmd}
        continue-on-error: true

      - name: Cortex — Store Test Result
        if: always()
        run: |
          cortex pr-context store \\
            --context-file .pr-context.json \\
            --test-result "${{{{ steps.tests.outcome }}}}"
{coverage_check}
      - name: Check Test Gate
        if: steps.tests.outcome != 'success'
        run: |
          echo "❌ Tests failed. Fix before merging."
          exit 1
"""

    @staticmethod
    def _step_documentation() -> str:
        return """\
      # ── Documentation Gate ───────────────────────────────────────
      - name: Cortex — Verify Agent Docs
        id: verify_docs
        if: always()
        run: |
          HAS_DOCS=$(cortex verify-docs --vault vault --output .doc-status.json || echo "false")
          echo "has_agent_docs=$HAS_DOCS" >> $GITHUB_OUTPUT
        continue-on-error: true

      - name: Cortex — Index Agent Docs
        if: always() && steps.verify_docs.outputs.has_agent_docs == 'true'
        run: |
          cortex index-docs --vault vault
          echo "✅ Agent documentation found and indexed"

      - name: Cortex — Generate Fallback Docs
        if: always() && steps.verify_docs.outputs.has_agent_docs != 'true'
        run: |
          cortex pr-context generate \\
            --context-file .pr-context.json \\
            --vault vault
          echo "⚠️ No agent docs — fallback session note generated"
        continue-on-error: true
"""
