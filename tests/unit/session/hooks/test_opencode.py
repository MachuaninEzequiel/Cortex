"""Tests for :class:`OpencodeHookAdapter` (Pluggable Middle Phase 05)."""

from __future__ import annotations

from pathlib import Path

from cortex.session.hooks.adapters.opencode import (
    HOOK_BLOCK,
    HOOKS_RELATIVE,
    START_MARKER,
    OpencodeHookAdapter,
)


class TestSupport:
    def test_is_supported_true(self) -> None:
        assert OpencodeHookAdapter().is_supported() is True

    def test_name(self) -> None:
        assert OpencodeHookAdapter().name == "opencode"


class TestInstall:
    def test_creates_hooks_file_when_absent(self, tmp_path: Path) -> None:
        adapter = OpencodeHookAdapter()
        result = adapter.install(tmp_path)
        target = tmp_path / HOOKS_RELATIVE
        assert result.installed is True
        assert result.modified_paths == [target]
        assert target.exists()
        body = target.read_text(encoding="utf-8")
        assert START_MARKER in body
        assert "cortex session checkpoint" in body

    def test_appends_to_existing_user_hooks(self, tmp_path: Path) -> None:
        adapter = OpencodeHookAdapter()
        target = tmp_path / HOOKS_RELATIVE
        target.parent.mkdir(parents=True)
        target.write_text(
            "# User hooks\n\nMy own hook content here.\n",
            encoding="utf-8",
        )
        adapter.install(tmp_path)
        body = target.read_text(encoding="utf-8")
        assert "My own hook content here." in body
        assert START_MARKER in body

    def test_idempotent(self, tmp_path: Path) -> None:
        adapter = OpencodeHookAdapter()
        first = adapter.install(tmp_path)
        second = adapter.install(tmp_path)
        assert first.installed is True
        assert second.installed is True
        assert second.modified_paths == []
        body = (tmp_path / HOOKS_RELATIVE).read_text(encoding="utf-8")
        # Marker only once.
        assert body.count(START_MARKER) == 1


class TestUninstall:
    def test_no_op_when_file_missing(self, tmp_path: Path) -> None:
        result = OpencodeHookAdapter().uninstall(tmp_path)
        assert result.uninstalled is False
        assert result.removed_paths == []

    def test_no_op_when_no_cortex_marker(self, tmp_path: Path) -> None:
        target = tmp_path / HOOKS_RELATIVE
        target.parent.mkdir(parents=True)
        target.write_text("# Just user content\n", encoding="utf-8")
        result = OpencodeHookAdapter().uninstall(tmp_path)
        assert result.uninstalled is False
        # File survives.
        assert target.exists()

    def test_preserves_user_hooks(self, tmp_path: Path) -> None:
        adapter = OpencodeHookAdapter()
        target = tmp_path / HOOKS_RELATIVE
        target.parent.mkdir(parents=True)
        target.write_text(
            "# User hooks\n\nMy own hook content here.\n",
            encoding="utf-8",
        )
        adapter.install(tmp_path)
        adapter.uninstall(tmp_path)
        body = target.read_text(encoding="utf-8")
        assert "My own hook content here." in body
        assert START_MARKER not in body

    def test_removes_file_when_only_cortex_block(self, tmp_path: Path) -> None:
        adapter = OpencodeHookAdapter()
        adapter.install(tmp_path)
        adapter.uninstall(tmp_path)
        # No user content was present → the file disappears entirely.
        assert not (tmp_path / HOOKS_RELATIVE).exists()


class TestStatus:
    def test_file_missing(self, tmp_path: Path) -> None:
        status = OpencodeHookAdapter().status(tmp_path)
        assert status.installed is False
        assert "does not exist" in status.detail

    def test_present_after_install(self, tmp_path: Path) -> None:
        adapter = OpencodeHookAdapter()
        adapter.install(tmp_path)
        status = adapter.status(tmp_path)
        assert status.installed is True

    def test_absent_after_uninstall(self, tmp_path: Path) -> None:
        adapter = OpencodeHookAdapter()
        adapter.install(tmp_path)
        adapter.uninstall(tmp_path)
        status = adapter.status(tmp_path)
        assert status.installed is False

    def test_malformed_file_reports_not_installed(self, tmp_path: Path) -> None:
        target = tmp_path / HOOKS_RELATIVE
        target.parent.mkdir(parents=True)
        target.write_text("garbage that doesn't contain the marker", encoding="utf-8")
        status = OpencodeHookAdapter().status(tmp_path)
        assert status.installed is False


class TestHookBlockShape:
    def test_block_includes_the_checkpoint_command(self) -> None:
        assert "cortex session checkpoint" in HOOK_BLOCK
        assert "--source ide-hook" in HOOK_BLOCK
        # Failure guard so opencode doesn't trip on Cortex errors.
        assert "|| true" in HOOK_BLOCK
