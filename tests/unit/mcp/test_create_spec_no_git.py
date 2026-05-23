"""Tests for the ``cortex_create_spec`` MCP handler in gitless workspaces.

When :class:`SpecService` opens the session in degraded mode (no git
detected), the MCP server must surface the situation to the caller via
the TOOL_RESULT text. This is the only way an LLM-driven agent learns
the workspace can't supply a git diff at close time and adjusts its
follow-up calls (e.g. it will not call ``cortex_session_checkpoint``
expecting diff-derived data).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from cortex.mcp.server import CortexMCPServer


@pytest.fixture
def cortex_repo_no_git(tmp_path: Path) -> Path:
    """A Cortex-aware workspace that deliberately lacks ``.git``."""
    repo = tmp_path / "repo_no_git"
    repo.mkdir()
    cortex_dir = repo / ".cortex"
    cortex_dir.mkdir()
    (cortex_dir / "workspace.yaml").write_text("layout_version: 2\n", encoding="utf-8")
    (cortex_dir / "config.yaml").write_text(
        "semantic:\n  vault_path: vault\nepisodic:\n  persist_dir: memory\n",
        encoding="utf-8",
    )
    (cortex_dir / "vault").mkdir()
    (cortex_dir / "vault" / "specs").mkdir()
    (cortex_dir / "memory").mkdir()
    return repo


@pytest.fixture
def cortex_repo_with_git(tmp_path: Path) -> Path:
    """A Cortex-aware workspace WITH git, for the contrast assertion."""
    repo = tmp_path / "repo_with_git"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@x.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True
    )
    cortex_dir = repo / ".cortex"
    cortex_dir.mkdir()
    (cortex_dir / "workspace.yaml").write_text("layout_version: 2\n", encoding="utf-8")
    (cortex_dir / "config.yaml").write_text(
        "semantic:\n  vault_path: vault\nepisodic:\n  persist_dir: memory\n",
        encoding="utf-8",
    )
    (cortex_dir / "vault").mkdir()
    (cortex_dir / "vault" / "specs").mkdir()
    (cortex_dir / "memory").mkdir()
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)
    return repo


def _server(repo: Path) -> CortexMCPServer:
    return CortexMCPServer(project_root=repo)


def _create_args() -> dict:
    return {"title": "demo", "goal": "anything"}


class TestCreateSpecGitless:
    def test_warning_appears_in_tool_result(
        self, cortex_repo_no_git: Path
    ) -> None:
        server = _server(cortex_repo_no_git)
        server._called_tools.add("cortex_sync_ticket")

        result = server._create_spec_text(_create_args())  # noqa: SLF001

        assert "Specification saved" in result
        # The notice is appended ONLY in gitless mode and uses a stable
        # marker string that downstream tests + the rich CLI can grep.
        assert "No git repository detected" in result
        assert "gitless" not in result.lower() or "degraded mode" in result

    def test_warning_includes_git_init_instructions(
        self, cortex_repo_no_git: Path
    ) -> None:
        server = _server(cortex_repo_no_git)
        server._called_tools.add("cortex_sync_ticket")

        result = server._create_spec_text(_create_args())  # noqa: SLF001

        assert "git init" in result
        assert "git add" in result
        assert "git commit" in result


class TestCreateSpecGitAware:
    def test_no_warning_when_git_is_available(
        self, cortex_repo_with_git: Path
    ) -> None:
        """The negative case: with git present, the notice MUST NOT appear."""
        server = _server(cortex_repo_with_git)
        server._called_tools.add("cortex_sync_ticket")

        result = server._create_spec_text(_create_args())  # noqa: SLF001

        assert "Specification saved" in result
        assert "No git repository detected" not in result
        assert "degraded mode" not in result
