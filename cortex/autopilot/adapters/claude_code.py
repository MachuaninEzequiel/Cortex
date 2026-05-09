"""cortex.autopilot.adapters.claude_code — Claude Code IDE adapter."""
from __future__ import annotations

from pathlib import Path

from cortex.autopilot.adapters.base import (
    _remove_autopilot_blocks,
    _write_with_backup,
    format_session_start_output,
)
from cortex.autopilot.models import AutopilotSessionState


class ClaudeCodeAutopilotAdapter:
    name = "claude-code"
    supported_events = {"session_start", "session_finish"}

    def install(self, project_root: Path) -> list[Path]:
        target = project_root / ".claude" / "autopilot-hook.md"
        marker = "<!-- AUTOPILOT-CLAUDE-CODE -->"
        block = (
            f"\n{marker}\n"
            "When a session starts, emit the Cortex Autopilot bootstrap context.\n"
            f"{marker}\n"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            text = target.read_text(encoding="utf-8")
            if marker in text:
                return []
            text += block
        else:
            text = block
        _write_with_backup(target, text)
        return [target]

    def uninstall(self, project_root: Path) -> list[Path]:
        target = project_root / ".claude" / "autopilot-hook.md"
        changed = _remove_autopilot_blocks(target, marker="<!-- AUTOPILOT-CLAUDE-CODE")
        return [target] if changed else []

    def emit_session_start(self, state: AutopilotSessionState, bootstrap: str) -> str:
        return format_session_start_output(state, bootstrap, "claude-code")
