"""cortex.autopilot.adapters.base — Base protocol and utilities for IDE adapters."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from cortex.autopilot.models import AutopilotSessionState


class AutopilotHookAdapter(Protocol):
    """Protocol for IDE-specific Autopilot hook adapters."""

    name: str
    supported_events: set[str]

    def install(self, project_root: Path) -> list[Path]:
        """Install hooks for this IDE. Returns list of modified paths."""
        ...

    def uninstall(self, project_root: Path) -> list[Path]:
        """Uninstall hooks for this IDE. Returns list of restored/removed paths."""
        ...

    def emit_session_start(self, state: AutopilotSessionState, bootstrap: str) -> str:
        """Return JSON formatted for this harness."""
        ...


def _backup_path(target: Path) -> Path:
    return target.with_suffix(target.suffix + ".autopilot-backup")


def _write_with_backup(target: Path, content: str) -> Path:
    """Write *content* to *target*, creating a backup if the file exists."""
    if target.exists():
        backup = _backup_path(target)
        target.rename(backup)
    target.write_text(content, encoding="utf-8")
    return target


def _restore_backup(target: Path) -> bool:
    """Restore *target* from its backup. Returns True if restored."""
    backup = _backup_path(target)
    if backup.exists():
        if target.exists():
            target.unlink()
        backup.rename(target)
        return True
    return False


def _remove_autopilot_blocks(path: Path, marker: str = "<!-- AUTOPILOT") -> bool:
    """Remove blocks delimited by *marker* from *path*. Returns True if changed."""
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    cleaned: list[str] = []
    inside_block = False
    changed = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(marker):
            inside_block = not inside_block
            changed = True
            continue
        if not inside_block:
            cleaned.append(line)
    if changed:
        path.write_text("".join(cleaned), encoding="utf-8")
    return changed


def format_session_start_output(
    state: AutopilotSessionState,
    bootstrap: str,
    platform_name: str,
) -> str:
    """Build the HookSessionStartOutput payload formatted for *platform_name*."""
    payload = {
        "session_id": state.session_id,
        "mode": state.mode,
        "bootstrap_content": bootstrap,
        "budget_profile": _budget_profile_for_state(state),
        "available_tools": [
            "cortex_autopilot_start",
            "cortex_autopilot_preflight",
            "cortex_autopilot_checkpoint",
            "cortex_autopilot_finish",
            "cortex_autopilot_status",
        ],
        "cortex_version": "3.0",
    }

    if platform_name == "cursor":
        return json.dumps({"additional_context": json.dumps(payload)})
    if platform_name == "claude-code":
        return json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": json.dumps(payload),
            }
        })
    return json.dumps({"additionalContext": json.dumps(payload)})


def _budget_profile_for_state(state: AutopilotSessionState) -> str:
    if state.detected_task_type == "question-only":
        return "question_only"
    if state.complexity == "deep":
        return "deep_task"
    if state.complexity == "fast":
        return "fast_code"
    return "fast_code"
