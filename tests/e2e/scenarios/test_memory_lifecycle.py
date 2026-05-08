"""Tests E2E: ciclo de vida de memoria (TASK 1-3)."""
from __future__ import annotations

import pytest

from tests.e2e.helpers import (
    assert_vault_has_documents,
    count_chroma_documents,
    run_cortex,
)


@pytest.mark.e2e
class TestMemoryLifecycle:
    """Valida remember → search → sync-vault end-to-end."""

    def test_remember_creates_episodic_entry(self, e2e_project_dir):
        run_cortex(
            e2e_project_dir,
            "setup", "agent", "--git-depth", "5", "--ide", "pi",
        )
        result = run_cortex(
            e2e_project_dir,
            "remember",
            "Test content about authentication",
            "--tag", "auth",
            "--tag", "test",
        )
        assert result.returncode == 0, result.stderr
        assert "mem_" in result.stdout

    def test_search_finds_remembered_content(self, e2e_project_dir):
        run_cortex(
            e2e_project_dir,
            "setup", "agent", "--git-depth", "5", "--ide", "pi",
        )
        run_cortex(
            e2e_project_dir,
            "remember",
            "Test content about authentication",
            "--tag", "auth",
        )
        result = run_cortex(
            e2e_project_dir,
            "search", "authentication",
            "--top-k", "5",
        )
        assert result.returncode == 0, result.stderr
        # Debe encontrar la memoria (por contenido o por ID)
        assert "authentication" in result.stdout.lower() or "mem_" in result.stdout

    def test_sync_vault_indexes_markdown(self, e2e_project_dir):
        run_cortex(
            e2e_project_dir,
            "setup", "agent", "--git-depth", "5", "--ide", "pi",
        )
        session_md = e2e_project_dir / ".cortex" / "vault" / "sessions" / "test.md"
        session_md.parent.mkdir(parents=True, exist_ok=True)
        session_md.write_text(
            '---\n'
            'tags: [test, session]\n'
            'timestamp: "2026-05-08T00:00:00"\n'
            '---\n\n'
            '# Test Session\n'
            'Content about testing strategies.\n',
            encoding="utf-8",
        )
        result = run_cortex(e2e_project_dir, "sync-vault")
        assert result.returncode == 0, result.stderr
        assert "1" in result.stdout or "indexed" in result.stdout.lower()

    def test_search_finds_vault_content(self, e2e_project_dir):
        run_cortex(
            e2e_project_dir,
            "setup", "agent", "--git-depth", "5", "--ide", "pi",
        )
        session_md = e2e_project_dir / ".cortex" / "vault" / "sessions" / "test.md"
        session_md.parent.mkdir(parents=True, exist_ok=True)
        session_md.write_text(
            '---\n'
            'tags: [test, session]\n'
            'timestamp: "2026-05-08T00:00:00"\n'
            '---\n\n'
            '# Test Session\n'
            'Content about testing strategies.\n',
            encoding="utf-8",
        )
        run_cortex(e2e_project_dir, "sync-vault")
        result = run_cortex(
            e2e_project_dir,
            "search", "testing strategies",
        )
        assert result.returncode == 0, result.stderr
        assert "Test Session" in result.stdout or "testing" in result.stdout.lower()
