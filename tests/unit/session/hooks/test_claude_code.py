"""Tests for :class:`ClaudeCodeHookAdapter` (T3.7)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cortex.session.hooks.adapters.claude_code import (
    CORTEX_HOOK_MARKER,
    ClaudeCodeHookAdapter,
)


@pytest.fixture
def adapter() -> ClaudeCodeHookAdapter:
    return ClaudeCodeHookAdapter()


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TestSupport:
    def test_is_supported_true(self, adapter: ClaudeCodeHookAdapter) -> None:
        assert adapter.is_supported() is True

    def test_name(self, adapter: ClaudeCodeHookAdapter) -> None:
        assert adapter.name == "claude-code"


class TestInstall:
    def test_creates_settings_file(
        self, adapter: ClaudeCodeHookAdapter, tmp_path: Path
    ) -> None:
        result = adapter.install(tmp_path)
        assert result.installed is True
        settings_path = tmp_path / ".claude" / "settings.json"
        assert settings_path.exists()
        data = _read(settings_path)
        assert data["hooks"]["PostToolUse"][0][CORTEX_HOOK_MARKER] is True

    def test_preserves_existing_settings(
        self, adapter: ClaudeCodeHookAdapter, tmp_path: Path
    ) -> None:
        settings = {"theme": "dark", "fontSize": 14}
        path = tmp_path / ".claude" / "settings.json"
        path.parent.mkdir()
        path.write_text(json.dumps(settings), encoding="utf-8")

        adapter.install(tmp_path)
        data = _read(path)
        assert data["theme"] == "dark"
        assert data["fontSize"] == 14
        assert "hooks" in data

    def test_preserves_other_user_hooks(
        self, adapter: ClaudeCodeHookAdapter, tmp_path: Path
    ) -> None:
        settings = {
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "Read",
                        "hooks": [{"type": "command", "command": "echo user-hook"}],
                    }
                ]
            }
        }
        path = tmp_path / ".claude" / "settings.json"
        path.parent.mkdir()
        path.write_text(json.dumps(settings), encoding="utf-8")

        adapter.install(tmp_path)
        data = _read(path)
        post_tool_use = data["hooks"]["PostToolUse"]
        assert len(post_tool_use) == 2
        assert any(e.get("matcher") == "Read" for e in post_tool_use)
        assert any(e.get(CORTEX_HOOK_MARKER) for e in post_tool_use)

    def test_idempotent(
        self, adapter: ClaudeCodeHookAdapter, tmp_path: Path
    ) -> None:
        first = adapter.install(tmp_path)
        second = adapter.install(tmp_path)
        assert first.installed is True
        assert second.installed is True
        assert "already installed" in second.message

        data = _read(tmp_path / ".claude" / "settings.json")
        entries = data["hooks"]["PostToolUse"]
        cortex_entries = [e for e in entries if e.get(CORTEX_HOOK_MARKER)]
        assert len(cortex_entries) == 1

    def test_install_rejects_non_object_root(
        self, adapter: ClaudeCodeHookAdapter, tmp_path: Path
    ) -> None:
        path = tmp_path / ".claude" / "settings.json"
        path.parent.mkdir()
        path.write_text("[1,2,3]", encoding="utf-8")
        with pytest.raises(ValueError, match="object at the root"):
            adapter.install(tmp_path)


class TestUninstall:
    def test_no_op_when_file_missing(
        self, adapter: ClaudeCodeHookAdapter, tmp_path: Path
    ) -> None:
        result = adapter.uninstall(tmp_path)
        assert result.uninstalled is False
        assert "does not exist" in result.message

    def test_no_op_when_no_cortex_entry(
        self, adapter: ClaudeCodeHookAdapter, tmp_path: Path
    ) -> None:
        path = tmp_path / ".claude" / "settings.json"
        path.parent.mkdir()
        path.write_text(json.dumps({"theme": "dark"}), encoding="utf-8")
        result = adapter.uninstall(tmp_path)
        assert result.uninstalled is False
        assert "no cortex-managed entry" in result.message

    def test_removes_cortex_entry_only(
        self, adapter: ClaudeCodeHookAdapter, tmp_path: Path
    ) -> None:
        # Pre-populate with a user hook AND the cortex hook.
        path = tmp_path / ".claude" / "settings.json"
        path.parent.mkdir()
        path.write_text(
            json.dumps(
                {
                    "theme": "dark",
                    "hooks": {
                        "PostToolUse": [
                            {
                                "matcher": "Read",
                                "hooks": [{"type": "command", "command": "echo X"}],
                            }
                        ]
                    },
                }
            ),
            encoding="utf-8",
        )
        adapter.install(tmp_path)

        result = adapter.uninstall(tmp_path)
        assert result.uninstalled is True
        data = _read(path)
        assert data["theme"] == "dark"
        assert data["hooks"]["PostToolUse"][0]["matcher"] == "Read"
        cortex_entries = [
            e
            for e in data["hooks"]["PostToolUse"]
            if e.get(CORTEX_HOOK_MARKER)
        ]
        assert cortex_entries == []

    def test_cleans_up_empty_containers(
        self, adapter: ClaudeCodeHookAdapter, tmp_path: Path
    ) -> None:
        adapter.install(tmp_path)
        adapter.uninstall(tmp_path)
        data = _read(tmp_path / ".claude" / "settings.json")
        # No leftover empty 'hooks' / 'PostToolUse' keys.
        assert "hooks" not in data


class TestStatus:
    def test_file_missing(
        self, adapter: ClaudeCodeHookAdapter, tmp_path: Path
    ) -> None:
        s = adapter.status(tmp_path)
        assert s.installed is False
        assert "does not exist" in s.detail

    def test_present(
        self, adapter: ClaudeCodeHookAdapter, tmp_path: Path
    ) -> None:
        adapter.install(tmp_path)
        s = adapter.status(tmp_path)
        assert s.installed is True
        assert "hook present" in s.detail

    def test_absent_after_uninstall(
        self, adapter: ClaudeCodeHookAdapter, tmp_path: Path
    ) -> None:
        adapter.install(tmp_path)
        adapter.uninstall(tmp_path)
        s = adapter.status(tmp_path)
        assert s.installed is False

    def test_malformed_json_reports_not_installed(
        self, adapter: ClaudeCodeHookAdapter, tmp_path: Path
    ) -> None:
        path = tmp_path / ".claude" / "settings.json"
        path.parent.mkdir()
        path.write_text("{not json", encoding="utf-8")
        s = adapter.status(tmp_path)
        assert s.installed is False
        assert "could not parse" in s.detail
