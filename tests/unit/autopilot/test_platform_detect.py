"""Tests for cortex.autopilot.adapters.platform_detect."""
from __future__ import annotations

import os

import pytest

from cortex.autopilot.adapters.platform_detect import Platform, detect_platform


class TestDetectPlatform:
    def test_cursor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CURSOR_PLUGIN_ROOT", "/cursor")
        assert detect_platform() == Platform.CURSOR

    def test_claude_code(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", "/claude")
        monkeypatch.delenv("COPILOT_CLI", raising=False)
        assert detect_platform() == Platform.CLAUDE_CODE

    def test_copilot_cli_takes_precedence_over_claude(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", "/claude")
        monkeypatch.setenv("COPILOT_CLI", "1")
        assert detect_platform() == Platform.COPILOT_CLI

    def test_opencode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENCODE_PLUGIN_ROOT", "/opencode")
        assert detect_platform() == Platform.OPENCODE

    def test_codex(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CODEX_PLUGIN_ROOT", "/codex")
        assert detect_platform() == Platform.CODEX

    def test_unknown(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for key in ("CURSOR_PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT", "COPILOT_CLI",
                    "OPENCODE_PLUGIN_ROOT", "CODEX_PLUGIN_ROOT"):
            monkeypatch.delenv(key, raising=False)
        assert detect_platform() == Platform.UNKNOWN
