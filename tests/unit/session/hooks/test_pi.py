"""Tests for :class:`PiHookAdapter` (T3.9)."""

from __future__ import annotations

from pathlib import Path

import pytest

from cortex.session.hooks.adapters.pi import (
    END_MARKER,
    RECIPE_BLOCK,
    START_MARKER,
    PiHookAdapter,
)


@pytest.fixture
def adapter() -> PiHookAdapter:
    return PiHookAdapter()


class TestSupport:
    def test_is_supported_true(self, adapter: PiHookAdapter) -> None:
        assert adapter.is_supported() is True

    def test_name(self, adapter: PiHookAdapter) -> None:
        assert adapter.name == "pi"


class TestInstall:
    def test_creates_justfile_when_absent(
        self, adapter: PiHookAdapter, tmp_path: Path
    ) -> None:
        result = adapter.install(tmp_path)
        path = tmp_path / "justfile"
        assert result.installed is True
        assert path.exists()
        assert "cortex-checkpoint" in path.read_text(encoding="utf-8")

    def test_appends_to_existing_justfile(
        self, adapter: PiHookAdapter, tmp_path: Path
    ) -> None:
        path = tmp_path / "justfile"
        path.write_text("hello:\n    echo hi\n", encoding="utf-8")
        adapter.install(tmp_path)
        content = path.read_text(encoding="utf-8")
        assert "echo hi" in content
        assert START_MARKER in content

    def test_idempotent(self, adapter: PiHookAdapter, tmp_path: Path) -> None:
        adapter.install(tmp_path)
        second = adapter.install(tmp_path)
        assert "already installed" in second.message
        path = tmp_path / "justfile"
        assert path.read_text(encoding="utf-8").count(START_MARKER) == 1


class TestUninstall:
    def test_no_op_when_file_missing(
        self, adapter: PiHookAdapter, tmp_path: Path
    ) -> None:
        result = adapter.uninstall(tmp_path)
        assert result.uninstalled is False
        assert "does not exist" in result.message

    def test_no_op_when_no_cortex_block(
        self, adapter: PiHookAdapter, tmp_path: Path
    ) -> None:
        path = tmp_path / "justfile"
        path.write_text("hello:\n    echo hi\n", encoding="utf-8")
        result = adapter.uninstall(tmp_path)
        assert result.uninstalled is False

    def test_preserves_user_recipes(
        self, adapter: PiHookAdapter, tmp_path: Path
    ) -> None:
        path = tmp_path / "justfile"
        path.write_text("hello:\n    echo hi\n", encoding="utf-8")
        adapter.install(tmp_path)
        adapter.uninstall(tmp_path)
        content = path.read_text(encoding="utf-8")
        assert "echo hi" in content
        assert START_MARKER not in content
        assert END_MARKER not in content

    def test_removes_file_when_only_cortex_block(
        self, adapter: PiHookAdapter, tmp_path: Path
    ) -> None:
        adapter.install(tmp_path)
        adapter.uninstall(tmp_path)
        assert not (tmp_path / "justfile").exists()


class TestStatus:
    def test_file_missing(self, adapter: PiHookAdapter, tmp_path: Path) -> None:
        s = adapter.status(tmp_path)
        assert s.installed is False

    def test_present(self, adapter: PiHookAdapter, tmp_path: Path) -> None:
        adapter.install(tmp_path)
        s = adapter.status(tmp_path)
        assert s.installed is True
        assert "recipes present" in s.detail


class TestRecipeBlockContent:
    def test_recipe_names(self) -> None:
        assert "cortex-checkpoint" in RECIPE_BLOCK
        assert "cortex-finish" in RECIPE_BLOCK
        assert "cortex-status" in RECIPE_BLOCK

    def test_uses_or_true_guard(self) -> None:
        # Every recipe must be defensive.
        assert RECIPE_BLOCK.count("|| true") >= 3
