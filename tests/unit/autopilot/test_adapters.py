"""Tests for cortex.autopilot.adapters and hooks."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cortex.autopilot.adapters.base import (
    _budget_profile_for_state,
    _remove_autopilot_blocks,
    _restore_backup,
    _write_with_backup,
    format_session_start_output,
)
from cortex.autopilot.adapters.claude_code import ClaudeCodeAutopilotAdapter
from cortex.autopilot.adapters.codex import CodexPluginAutopilotAdapter
from cortex.autopilot.adapters.cursor import CursorAutopilotAdapter
from cortex.autopilot.adapters.opencode import OpenCodeAutopilotAdapter
from cortex.autopilot.adapters.platform_detect import Platform, detect_platform
from cortex.autopilot.adapters.registry import (
    get_adapter,
    get_adapter_for_current_platform,
    list_adapters,
)
from cortex.autopilot.hooks.session_finish import emit as finish_emit
from cortex.autopilot.hooks.session_start import emit as start_emit
from cortex.autopilot.models import AutopilotSessionState


class TestBaseUtilities:
    def test_write_with_backup_creates_backup(self, tmp_path: Path) -> None:
        target = tmp_path / "config.txt"
        target.write_text("original")
        _write_with_backup(target, "modified")
        assert target.read_text() == "modified"
        backup = tmp_path / "config.txt.autopilot-backup"
        assert backup.exists()
        assert backup.read_text() == "original"

    def test_restore_backup(self, tmp_path: Path) -> None:
        target = tmp_path / "config.txt"
        target.write_text("original")
        _write_with_backup(target, "modified")
        assert _restore_backup(target)
        assert target.read_text() == "original"

    def test_remove_autopilot_blocks(self, tmp_path: Path) -> None:
        target = tmp_path / "config.md"
        target.write_text(
            "before\n<!-- AUTOPILOT-X -->\ninside\n<!-- AUTOPILOT-X -->\nafter\n"
        )
        assert _remove_autopilot_blocks(target, marker="<!-- AUTOPILOT-X")
        assert target.read_text() == "before\nafter\n"

    def test_budget_profile_question_only(self) -> None:
        state = AutopilotSessionState(
            session_id="s1",
            project_root="/r",
            workspace_root="/r/.cortex",
            detected_task_type="question-only",
        )
        assert _budget_profile_for_state(state) == "question_only"

    def test_budget_profile_fast_code_low(self) -> None:
        state = AutopilotSessionState(
            session_id="s1", project_root="/r", workspace_root="/r/.cortex", complexity="fast"
        )
        assert _budget_profile_for_state(state) == "fast_code"

    def test_budget_profile_deep_task_high(self) -> None:
        state = AutopilotSessionState(
            session_id="s1", project_root="/r", workspace_root="/r/.cortex", complexity="deep"
        )
        assert _budget_profile_for_state(state) == "deep_task"


class TestCursorAdapter:
    def test_install_and_uninstall(self, tmp_path: Path) -> None:
        adapter = CursorAutopilotAdapter()
        modified = adapter.install(tmp_path)
        assert len(modified) == 1
        assert modified[0].exists()
        removed = adapter.uninstall(tmp_path)
        assert len(removed) == 1
        # The marker should be gone
        text = modified[0].read_text()
        assert "AUTOPILOT-CURSOR" not in text

    def test_emit_session_start(self) -> None:
        adapter = CursorAutopilotAdapter()
        state = AutopilotSessionState(session_id="sid", mode="assist", project_root="/r", workspace_root="/r/.cortex")
        payload = adapter.emit_session_start(state, "bootstrap")
        data = json.loads(payload)
        assert "additional_context" in data
        inner = json.loads(data["additional_context"])
        assert inner["session_id"] == "sid"
        assert inner["mode"] == "assist"

    def test_supported_events(self) -> None:
        assert "session_start" in CursorAutopilotAdapter.supported_events


class TestClaudeCodeAdapter:
    def test_install_and_uninstall(self, tmp_path: Path) -> None:
        adapter = ClaudeCodeAutopilotAdapter()
        modified = adapter.install(tmp_path)
        assert len(modified) == 1
        removed = adapter.uninstall(tmp_path)
        assert len(removed) == 1

    def test_emit_session_start(self) -> None:
        adapter = ClaudeCodeAutopilotAdapter()
        state = AutopilotSessionState(session_id="sid", mode="autopilot", project_root="/r", workspace_root="/r/.cortex")
        payload = adapter.emit_session_start(state, "bootstrap")
        data = json.loads(payload)
        assert "hookSpecificOutput" in data
        assert data["hookSpecificOutput"]["hookEventName"] == "SessionStart"


class TestOpenCodeAdapter:
    def test_install_and_uninstall(self, tmp_path: Path) -> None:
        adapter = OpenCodeAutopilotAdapter()
        modified = adapter.install(tmp_path)
        assert len(modified) == 1
        removed = adapter.uninstall(tmp_path)
        assert len(removed) == 1

    def test_emit_session_start(self) -> None:
        adapter = OpenCodeAutopilotAdapter()
        state = AutopilotSessionState(session_id="sid", project_root="/r", workspace_root="/r/.cortex")
        payload = adapter.emit_session_start(state, "")
        data = json.loads(payload)
        assert "additionalContext" in data


class TestCodexAdapter:
    def test_install_and_uninstall(self, tmp_path: Path) -> None:
        adapter = CodexPluginAutopilotAdapter()
        modified = adapter.install(tmp_path)
        assert len(modified) == 1
        removed = adapter.uninstall(tmp_path)
        assert len(removed) == 1

    def test_emit_session_start(self) -> None:
        adapter = CodexPluginAutopilotAdapter()
        state = AutopilotSessionState(session_id="sid", project_root="/r", workspace_root="/r/.cortex")
        payload = adapter.emit_session_start(state, "")
        data = json.loads(payload)
        assert "additionalContext" in data


class TestRegistry:
    def test_list_adapters(self) -> None:
        names = list_adapters()
        assert sorted(names) == ["claude-code", "codex", "cursor", "opencode"]

    def test_get_adapter(self) -> None:
        assert get_adapter("cursor") is CursorAutopilotAdapter
        assert get_adapter("claude-code") is ClaudeCodeAutopilotAdapter

    def test_get_adapter_unknown(self) -> None:
        with pytest.raises(KeyError):
            get_adapter("vscode")

    def test_get_adapter_for_current_platform(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CURSOR_PLUGIN_ROOT", "/cursor")
        assert get_adapter_for_current_platform() is CursorAutopilotAdapter

    def test_get_adapter_for_current_platform_unknown(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for key in ("CURSOR_PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT", "COPILOT_CLI",
                    "OPENCODE_PLUGIN_ROOT", "CODEX_PLUGIN_ROOT"):
            monkeypatch.delenv(key, raising=False)
        assert get_adapter_for_current_platform() is None


class TestFormatSessionStartOutput:
    def test_cursor_format(self) -> None:
        state = AutopilotSessionState(session_id="s1", mode="assist", project_root="/r", workspace_root="/r/.cortex")
        raw = format_session_start_output(state, "boot", "cursor")
        data = json.loads(raw)
        inner = json.loads(data["additional_context"])
        assert inner["session_id"] == "s1"
        assert inner["cortex_version"] == "3.0"

    def test_claude_format(self) -> None:
        state = AutopilotSessionState(session_id="s1", mode="autopilot", project_root="/r", workspace_root="/r/.cortex")
        raw = format_session_start_output(state, "boot", "claude-code")
        data = json.loads(raw)
        assert data["hookSpecificOutput"]["hookEventName"] == "SessionStart"

    def test_default_format(self) -> None:
        state = AutopilotSessionState(session_id="s1", project_root="/r", workspace_root="/r/.cortex")
        raw = format_session_start_output(state, "boot", "codex")
        data = json.loads(raw)
        assert "additionalContext" in data


class TestSessionStartHook:
    def test_emit_no_session(self, tmp_path: Path) -> None:
        result = start_emit(tmp_path)
        assert "error" in result

    def test_emit_with_session(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cortex.autopilot.lifecycle import StartRequest
        from cortex.autopilot.service import AutopilotService

        svc = AutopilotService.from_project_root(tmp_path)
        start_res = svc.start(StartRequest(project_root=str(tmp_path), workspace_root=str(tmp_path)))

        monkeypatch.setenv("CURSOR_PLUGIN_ROOT", "/cursor")
        payload = start_emit(tmp_path, start_res.session_id)
        data = json.loads(payload)
        assert "additional_context" in data


class TestSessionFinishHook:
    def test_emit_no_session(self, tmp_path: Path) -> None:
        result = finish_emit(tmp_path)
        assert json.loads(result)["error"] == "No active Autopilot session"

    def test_emit_with_session(self, tmp_path: Path) -> None:
        from cortex.autopilot.lifecycle import StartRequest
        from cortex.autopilot.service import AutopilotService

        svc = AutopilotService.from_project_root(tmp_path)
        start_res = svc.start(StartRequest(project_root=str(tmp_path), workspace_root=str(tmp_path)))

        payload = finish_emit(tmp_path, start_res.session_id)
        data = json.loads(payload)
        assert data["event"] == "SessionFinish"
        assert data["session_id"] == start_res.session_id
