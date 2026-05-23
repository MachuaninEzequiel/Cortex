"""Tests for :func:`cortex.ci.diff_io.read_diff_from_args`."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from cortex.ci.diff_io import DiffResolutionError, read_diff_from_args


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@x.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True)
    (repo / "x.txt").write_text("v1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)
    return repo


def _make_second_commit(repo: Path) -> str:
    (repo / "x.txt").write_text("v1\nv2\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "v2"], cwd=repo, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


class TestReadDiff:
    def test_from_file(self, tmp_path: Path, repo: Path) -> None:
        diff_path = tmp_path / "in.diff"
        diff_path.write_text("--- a/x\n+++ b/x\n+new\n", encoding="utf-8")
        out = read_diff_from_args(
            diff_file=diff_path,
            base_commit=None,
            head_commit=None,
            repo_root=repo,
        )
        assert "+new" in out

    def test_missing_diff_file_raises(self, tmp_path: Path, repo: Path) -> None:
        with pytest.raises(DiffResolutionError, match="not found"):
            read_diff_from_args(
                diff_file=tmp_path / "missing.diff",
                base_commit=None,
                head_commit=None,
                repo_root=repo,
            )

    def test_from_commits(self, repo: Path) -> None:
        base = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        head = _make_second_commit(repo)
        out = read_diff_from_args(
            diff_file=None,
            base_commit=base,
            head_commit=head,
            repo_root=repo,
        )
        assert "+v2" in out

    def test_auto_detect_main(self, repo: Path) -> None:
        # Switch to a branch so HEAD differs from main; commit something.
        subprocess.run(["git", "checkout", "-qb", "feature"], cwd=repo, check=True)
        _make_second_commit(repo)
        out = read_diff_from_args(
            diff_file=None,
            base_commit=None,
            head_commit=None,
            repo_root=repo,
        )
        assert "+v2" in out

    def test_no_trunk_raises(self, tmp_path: Path) -> None:
        # Build a repo with no main or master branch.
        repo = tmp_path / "repo2"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "trunk"], cwd=repo, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@x.com"], cwd=repo, check=True
        )
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
        subprocess.run(
            ["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True
        )
        (repo / "f.txt").write_text("x\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)

        with pytest.raises(DiffResolutionError, match="auto-detect"):
            read_diff_from_args(
                diff_file=None,
                base_commit=None,
                head_commit=None,
                repo_root=repo,
            )
