"""Tests for :mod:`cortex.session.git` using real git in a temporary repo."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from cortex.session.git import (
    GitError,
    diff,
    diff_name_status,
    get_current_branch,
    get_head_commit,
)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=repo,
        check=True,
    )
    (repo / "README.md").write_text("hi\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    return repo


class TestGetHeadCommit:
    def test_returns_40_char_hex_sha(self, git_repo: Path) -> None:
        sha = get_head_commit(git_repo)
        assert len(sha) == 40
        assert all(c in "0123456789abcdef" for c in sha)

    def test_raises_on_non_git_dir(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(GitError):
            get_head_commit(empty)


class TestGetCurrentBranch:
    def test_returns_branch_name(self, git_repo: Path) -> None:
        branch = get_current_branch(git_repo)
        assert branch == "main"

    def test_detached_head_returns_head(self, git_repo: Path) -> None:
        sha = get_head_commit(git_repo)
        subprocess.run(["git", "checkout", "-q", sha], cwd=git_repo, check=True)
        assert get_current_branch(git_repo) == "HEAD"


class TestDiff:
    def test_diff_between_two_commits(self, git_repo: Path) -> None:
        first_sha = get_head_commit(git_repo)
        (git_repo / "second.txt").write_text("hello\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "second"], cwd=git_repo, check=True)
        second_sha = get_head_commit(git_repo)

        out = diff(first_sha, second_sha, git_repo)
        assert "second.txt" in out
        assert "hello" in out

    def test_empty_diff_when_no_changes(self, git_repo: Path) -> None:
        sha = get_head_commit(git_repo)
        assert diff(sha, sha, git_repo) == ""


class TestDiffNameStatus:
    def test_added_file_marked_A(self, git_repo: Path) -> None:
        first_sha = get_head_commit(git_repo)
        (git_repo / "new.txt").write_text("new\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "add new"], cwd=git_repo, check=True)
        out = diff_name_status(first_sha, "HEAD", git_repo)
        assert out.strip().startswith("A\t")
        assert "new.txt" in out

    def test_modified_file_marked_M(self, git_repo: Path) -> None:
        first_sha = get_head_commit(git_repo)
        (git_repo / "README.md").write_text("changed\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "edit"], cwd=git_repo, check=True)
        out = diff_name_status(first_sha, "HEAD", git_repo)
        assert "M\tREADME.md" in out

    def test_empty_when_no_changes(self, git_repo: Path) -> None:
        sha = get_head_commit(git_repo)
        assert diff_name_status(sha, sha, git_repo) == ""


class TestGitErrors:
    def test_invalid_command_raises_git_error(self, git_repo: Path) -> None:
        with pytest.raises(GitError, match="failed"):
            diff("not-a-ref", "HEAD", git_repo)

    def test_missing_git_executable_raises_git_error(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Simulate ``git`` missing on PATH by making subprocess.run raise.
        import subprocess as sp

        def _no_git(*args: object, **kwargs: object) -> object:
            raise FileNotFoundError(2, "git", "not on PATH")

        monkeypatch.setattr(sp, "run", _no_git)
        with pytest.raises(GitError, match="not found on PATH"):
            get_head_commit(git_repo)

    def test_unexpected_rev_parse_output_raises_git_error(
        self, git_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Hijack the internal subprocess wrapper so it returns a value that
        # fails the SHA shape check (the defensive guard on line 48 of git.py).
        from cortex.session import git as git_module

        def _bad_run(args: list[str], repo_root: Path) -> str:
            assert args[0] == "rev-parse"
            return "not-a-sha\n"

        monkeypatch.setattr(git_module, "_run", _bad_run)
        with pytest.raises(GitError, match="unexpected output"):
            get_head_commit(git_repo)
