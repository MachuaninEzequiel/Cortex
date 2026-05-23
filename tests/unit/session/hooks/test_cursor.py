"""Tests for :class:`CursorGitHookAdapter` (T3.8)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from cortex.session.hooks.adapters.cursor import (
    END_MARKER,
    HOOK_BLOCK,
    START_MARKER,
    CursorGitHookAdapter,
)


@pytest.fixture
def adapter() -> CursorGitHookAdapter:
    return CursorGitHookAdapter()


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git" / "hooks").mkdir(parents=True)
    return repo


class TestSupport:
    def test_is_supported_true(self, adapter: CursorGitHookAdapter) -> None:
        assert adapter.is_supported() is True

    def test_name(self, adapter: CursorGitHookAdapter) -> None:
        assert adapter.name == "cursor"


class TestInstall:
    def test_creates_hook_file_when_absent(
        self, adapter: CursorGitHookAdapter, git_repo: Path
    ) -> None:
        result = adapter.install(git_repo)
        hook = git_repo / ".git" / "hooks" / "post-commit"
        assert result.installed is True
        assert hook.exists()
        content = hook.read_text(encoding="utf-8")
        assert START_MARKER in content
        assert "cortex session checkpoint" in content

    def test_rejects_when_not_a_git_repo(
        self, adapter: CursorGitHookAdapter, tmp_path: Path
    ) -> None:
        # tmp_path is NOT a git repo.
        with pytest.raises(ValueError, match="not a git repository"):
            adapter.install(tmp_path / "no-git")

    def test_appends_to_existing_user_hook(
        self, adapter: CursorGitHookAdapter, git_repo: Path
    ) -> None:
        hook = git_repo / ".git" / "hooks" / "post-commit"
        hook.write_text("#!/bin/sh\necho user-hook\n", encoding="utf-8")
        adapter.install(git_repo)
        content = hook.read_text(encoding="utf-8")
        assert "echo user-hook" in content
        assert START_MARKER in content

    def test_idempotent(
        self, adapter: CursorGitHookAdapter, git_repo: Path
    ) -> None:
        adapter.install(git_repo)
        second = adapter.install(git_repo)
        assert "already installed" in second.message
        # Marker should appear exactly once.
        hook = git_repo / ".git" / "hooks" / "post-commit"
        content = hook.read_text(encoding="utf-8")
        assert content.count(START_MARKER) == 1

    @pytest.mark.skipif(sys.platform == "win32", reason="chmod has no effect on Windows")
    def test_sets_executable_bit_on_unix(
        self, adapter: CursorGitHookAdapter, git_repo: Path
    ) -> None:
        adapter.install(git_repo)
        hook = git_repo / ".git" / "hooks" / "post-commit"
        assert hook.stat().st_mode & 0o111  # any execute bit set


class TestUninstall:
    def test_no_op_when_file_missing(
        self, adapter: CursorGitHookAdapter, git_repo: Path
    ) -> None:
        result = adapter.uninstall(git_repo)
        assert result.uninstalled is False
        assert "does not exist" in result.message

    def test_no_op_when_no_cortex_block(
        self, adapter: CursorGitHookAdapter, git_repo: Path
    ) -> None:
        hook = git_repo / ".git" / "hooks" / "post-commit"
        hook.write_text("#!/bin/sh\necho user\n", encoding="utf-8")
        result = adapter.uninstall(git_repo)
        assert result.uninstalled is False
        assert "no cortex-managed block" in result.message

    def test_preserves_user_hook(
        self, adapter: CursorGitHookAdapter, git_repo: Path
    ) -> None:
        hook = git_repo / ".git" / "hooks" / "post-commit"
        hook.write_text("#!/bin/sh\necho user-hook\n", encoding="utf-8")
        adapter.install(git_repo)
        adapter.uninstall(git_repo)
        content = hook.read_text(encoding="utf-8")
        assert "echo user-hook" in content
        assert START_MARKER not in content
        assert END_MARKER not in content

    def test_removes_file_when_only_cortex_block(
        self, adapter: CursorGitHookAdapter, git_repo: Path
    ) -> None:
        adapter.install(git_repo)
        adapter.uninstall(git_repo)
        hook = git_repo / ".git" / "hooks" / "post-commit"
        assert not hook.exists()


class TestStatus:
    def test_file_missing(
        self, adapter: CursorGitHookAdapter, git_repo: Path
    ) -> None:
        s = adapter.status(git_repo)
        assert s.installed is False
        assert "does not exist" in s.detail

    def test_present(self, adapter: CursorGitHookAdapter, git_repo: Path) -> None:
        adapter.install(git_repo)
        s = adapter.status(git_repo)
        assert s.installed is True
        assert "cortex block present" in s.detail

    def test_absent_after_uninstall(
        self, adapter: CursorGitHookAdapter, git_repo: Path
    ) -> None:
        adapter.install(git_repo)
        adapter.uninstall(git_repo)
        s = adapter.status(git_repo)
        assert s.installed is False


class TestHookBlockContents:
    def test_uses_or_true_guard(self) -> None:
        assert "|| true" in HOOK_BLOCK

    def test_invokes_cortex_session_checkpoint(self) -> None:
        assert "cortex session checkpoint" in HOOK_BLOCK
        assert "--source ide-hook" in HOOK_BLOCK


# Quiet unused-import warnings under static analysis.
_ = os
