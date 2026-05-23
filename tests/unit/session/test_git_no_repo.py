"""Tests for the gitless-mode helpers in :mod:`cortex.session.git`.

Covers:
    * ``is_git_repo`` returns False on a directory with no .git.
    * ``try_get_head_commit`` / ``try_get_current_branch`` return None on
      failure instead of raising.
    * ``_run`` enforces the subprocess timeout (raises ``GitError``).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from cortex.session import git as session_git
from cortex.session.git import (
    GitError,
    is_git_repo,
    try_get_current_branch,
    try_get_head_commit,
)

# ---------------------------------------------------------------------------
# is_git_repo
# ---------------------------------------------------------------------------


def test_is_git_repo_returns_false_on_empty_dir(tmp_path: Path) -> None:
    """A fresh directory without ``.git/`` is not a repo."""
    assert is_git_repo(tmp_path) is False


def test_is_git_repo_returns_true_on_initialised_repo(tmp_path: Path) -> None:
    """A directory after ``git init`` reports as a repo."""
    subprocess.run(
        ["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True
    )
    assert is_git_repo(tmp_path) is True


# ---------------------------------------------------------------------------
# try_get_head_commit / try_get_current_branch
# ---------------------------------------------------------------------------


def test_try_get_head_commit_returns_none_without_git(tmp_path: Path) -> None:
    assert try_get_head_commit(tmp_path) is None


def test_try_get_current_branch_returns_none_without_git(tmp_path: Path) -> None:
    assert try_get_current_branch(tmp_path) is None


def test_try_get_head_commit_returns_sha_on_real_repo(tmp_path: Path) -> None:
    """Once there's a commit, the soft variant returns the SHA."""
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@x.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True
    )
    (tmp_path / "README.md").write_text("seed", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=tmp_path, check=True)

    sha = try_get_head_commit(tmp_path)
    assert sha is not None
    assert len(sha) == 40
    assert all(c in "0123456789abcdef" for c in sha)


# ---------------------------------------------------------------------------
# Subprocess timeout enforcement
# ---------------------------------------------------------------------------


def test_run_raises_giterror_on_timeout(tmp_path: Path) -> None:
    """If git takes longer than the budget, ``_run`` surfaces a GitError.

    Mocks ``subprocess.run`` to raise ``TimeoutExpired``; the real value
    of the timeout (10s) doesn't matter for this test — we only care that
    the wrapper translates the exception correctly.
    """
    with patch.object(
        session_git.subprocess,
        "run",
        side_effect=subprocess.TimeoutExpired(cmd=["git"], timeout=10.0),
    ), pytest.raises(GitError) as exc:
        session_git._run(["rev-parse", "HEAD"], tmp_path)
    msg = str(exc.value)
    assert "timed out" in msg
    assert "rev-parse" in msg


def test_is_git_repo_returns_false_on_timeout(tmp_path: Path) -> None:
    """A timed-out probe is treated as "not a repo" (degrade gracefully)."""
    with patch.object(
        session_git.subprocess,
        "run",
        side_effect=subprocess.TimeoutExpired(cmd=["git"], timeout=10.0),
    ):
        assert is_git_repo(tmp_path) is False
