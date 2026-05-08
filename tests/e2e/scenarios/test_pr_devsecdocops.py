"""Tests E2E: pipeline PR / DevSecDocOps (TASK 1-5)."""
from __future__ import annotations

import json

import pytest

from tests.e2e.helpers import (
    assert_vault_has_documents,
    run_cortex,
)


@pytest.mark.e2e
class TestPrDevSecDocOps:
    """Valida cortex pr-context end-to-end."""

    def test_pr_context_full_generates_docs(self, e2e_project_dir):
        run_cortex(
            e2e_project_dir,
            "setup", "agent", "--git-depth", "5", "--ide", "pi",
        )
        result = run_cortex(
            e2e_project_dir,
            "pr-context", "full",
            "--title", "Test PR",
            "--body", "Testing the DevSecDocOps pipeline",
            "--author", "tester",
            "--branch", "feature/test",
            "--commit", "abc123",
            "--pr-number", "42",
            "--vault", ".cortex/vault",
        )
        assert result.returncode == 0, result.stderr
        assert "DevSecDocOps pipeline complete" in result.stdout
        assert_vault_has_documents(e2e_project_dir / ".cortex" / "vault", min_count=1)

    def test_pr_context_full_stores_in_memory(self, e2e_project_dir):
        run_cortex(
            e2e_project_dir,
            "setup", "agent", "--git-depth", "5", "--ide", "pi",
        )
        run_cortex(
            e2e_project_dir,
            "pr-context", "full",
            "--title", "Test PR",
            "--body", "Testing the DevSecDocOps pipeline",
            "--author", "tester",
            "--branch", "feature/test",
            "--commit", "abc123",
            "--pr-number", "42",
            "--vault", ".cortex/vault",
        )
        result = run_cortex(e2e_project_dir, "search", "Test PR")
        assert result.returncode == 0, result.stderr
        assert "tester" in result.stdout.lower() or "pr" in result.stdout.lower()

    def test_pr_context_capture_standalone(self, e2e_project_dir):
        result = run_cortex(
            e2e_project_dir,
            "pr-context", "capture",
            "--title", "Standalone",
            "--output", ".pr-context.json",
        )
        assert result.returncode == 0, result.stderr
        path = e2e_project_dir / ".pr-context.json"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("title") == "Standalone"
