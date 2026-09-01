//! Puerto de `runners/github.py`: generador puro de workflow YAML.
//! Los f-strings con `{{ }}` de Python se vuelven literales `{ }`.

pub struct GitHubActionsRunner {
    python_version: String,
    runs_on: String,
    branches: Vec<String>,
}

impl Default for GitHubActionsRunner {
    fn default() -> Self {
        Self::new("3.11", "ubuntu-latest", None)
    }
}

impl GitHubActionsRunner {
    pub fn new(python_version: &str, runs_on: &str, branches: Option<Vec<String>>) -> Self {
        Self {
            python_version: python_version.into(),
            runs_on: runs_on.into(),
            branches: branches.unwrap_or_else(|| vec!["main".into(), "master".into()]),
        }
    }

    pub fn generate_pr_workflow(&self, stages: &[crate::domain::types::StageType]) -> String {
        let branch_list = self
            .branches
            .iter()
            .map(|b| format!("      - '{b}'"))
            .collect::<Vec<_>>()
            .join("\n");
        let steps = self.build_steps(stages);
        format!(
            r#"name: Cortex DevSecDocOps — PR Validation

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
    runs-on: {runs_on}

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Python {py}
        uses: actions/setup-python@v5
        with:
          python-version: '{py}'

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
          pip install -e '.[dev]'

      - name: Cortex — Capture PR Context
        id: capture
        run: |
          cortex pr-context capture \
            --title "${{{{ github.event.pull_request.title }}}}" \
            --body "${{{{ github.event.pull_request.body || '' }}}}" \
            --author "${{{{ github.event.pull_request.user.login }}}}" \
            --branch "${{{{ github.event.pull_request.head.ref }}}}" \
            --commit "${{{{ github.event.pull_request.head.sha }}}}" \
            --pr-number "${{{{ github.event.pull_request.number }}}}" \
            --target-branch "${{{{ github.event.pull_request.base.ref }}}}" \
            --labels "${{{{ join(github.event.pull_request.labels.*.name, ',') }}}}" \
            --output .pr-context.json

{steps}

      - name: Cortex — Search Past Context
        if: always()
        run: |
          cortex pr-context search \
            --context-file .pr-context.json \
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
"#,
            branch_list = branch_list,
            runs_on = self.runs_on,
            py = self.python_version,
            steps = steps,
        )
    }

    fn build_steps(&self, stages: &[crate::domain::types::StageType]) -> String {
        use crate::domain::types::StageType::*;
        let mut blocks = Vec::new();
        for stage_type in stages {
            match stage_type {
                SecurityScan => blocks.push(super::github::step_security("pip-audit")),
                Lint => blocks.push(super::github::step_lint("ruff check .")),
                Test => blocks.push(super::github::step_test(
                    "pytest --cov=. --cov-report=term-missing -q",
                    0,
                )),
                Documentation => blocks.push(super::github::step_documentation()),
                _ => {}
            }
        }
        blocks.join("\n")
    }
}

fn step_security(audit_cmd: &str) -> String {
    format!(
        r#"      # ── Security Gate ────────────────────────────────────────────
      - name: Security Audit
        id: security
        run: {audit_cmd}
        continue-on-error: true

      - name: Cortex — Store Security Result
        if: always()
        run: |
          cortex pr-context store \
            --context-file .pr-context.json \
            --audit-result "${{{{ steps.security.outcome }}}}"

      - name: Check Security Gate
        if: steps.security.outcome != 'success'
        run: |
          echo "❌ Security audit failed. Review vulnerabilities before merging."
          exit 1
"#
    )
}

fn step_lint(lint_cmd: &str) -> String {
    format!(
        r#"      # ── Lint Gate ────────────────────────────────────────────────
      - name: Lint
        id: lint
        run: {lint_cmd}
        continue-on-error: true

      - name: Cortex — Store Lint Result
        if: always()
        run: |
          cortex pr-context store \
            --context-file .pr-context.json \
            --lint-result "${{{{ steps.lint.outcome }}}}"

      - name: Check Lint Gate
        if: steps.lint.outcome != 'success'
        run: |
          echo "❌ Lint check failed. Fix errors before merging."
          exit 1
"#
    )
}

fn step_test(test_cmd: &str, min_coverage: i64) -> String {
    let coverage_check = if min_coverage > 0 {
        format!(
            r#"
      - name: Check Coverage Gate
        if: steps.tests.outcome == 'success'
        run: |
          COVERAGE=$(python -c "
          import re, sys
          output = open('/tmp/test-output.txt').read()
          m = re.search(r'TOTAL.*?(\d+)%', output)
          print(m.group(1) if m else '0')
          " 2>/dev/null || echo "0")
          if [ "$COVERAGE" -lt "{min_coverage}" ]; then
            echo "❌ Coverage $COVERAGE% is below minimum {min_coverage}%"
            exit 1
          fi
          echo "✅ Coverage $COVERAGE% meets minimum {min_coverage}%"
"#
        )
    } else {
        String::new()
    };
    format!(
        r#"      # ── Test Gate ────────────────────────────────────────────────
      - name: Tests
        id: tests
        run: |
          {test_cmd} 2>&1 | tee /tmp/test-output.txt
          exit ${{{{ PIPESTATUS[0] }}}}
        continue-on-error: true

      - name: Cortex — Store Test Result
        if: always()
        run: |
          cortex pr-context store \
            --context-file .pr-context.json \
            --test-result "${{{{ steps.tests.outcome }}}}"
{coverage_check}
      - name: Check Test Gate
        if: steps.tests.outcome != 'success'
        run: |
          echo "❌ Tests failed. Fix before merging."
          exit 1
"#,
        test_cmd = test_cmd,
        coverage_check = coverage_check,
    )
}

fn step_documentation() -> String {
    r#"      # ── Documentation Gate ───────────────────────────────────────
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
          cortex pr-context generate \
            --context-file .pr-context.json \
            --vault vault
          echo "⚠️ No agent docs — fallback session note generated"
        continue-on-error: true
"#
    .to_string()
}
