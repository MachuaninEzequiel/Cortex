"""cortex.autopilot.hooks.session_start — Emit session-start payload for the IDE harness.

This module is designed to be called as a script or via ``python -m``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cortex.autopilot.adapters.platform_detect import Platform, detect_platform
from cortex.autopilot.adapters.registry import get_adapter_for_current_platform
from cortex.autopilot.service import AutopilotService
from cortex.ide.prompts import get_skill_prompt


def emit(
    project_root: str | Path,
    session_id: str | None = None,
) -> str:
    """Emit the session-start JSON for the detected platform.

    Args:
        project_root: Path to the project root.
        session_id: Optional explicit session ID. If omitted, uses the active
            session from the state store.

    Returns:
        JSON string formatted for the current harness.
    """
    root = Path(project_root)
    svc = AutopilotService.from_project_root(root)

    status = svc.status(session_id)
    if not status.active or status.state is None:
        return "{\"error\": \"No active Autopilot session\"}"

    state = status.state

    # Load bootstrap content from the workspace skill (with fallback)
    bootstrap = get_skill_prompt(root, "using-cortex-autopilot")

    adapter_cls = get_adapter_for_current_platform()
    if adapter_cls is None:
        platform = detect_platform()
        return f'{{"error": "Unsupported platform: {platform.value}"}}'

    adapter = adapter_cls()
    return adapter.emit_session_start(state, bootstrap)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit Autopilot session-start hook")
    parser.add_argument("--project-root", required=True, help="Project root path")
    parser.add_argument("--session-id", default=None, help="Explicit session ID")
    args = parser.parse_args(argv)

    try:
        print(emit(args.project_root, args.session_id))
        return 0
    except Exception as exc:
        print(f'{{"error": "{type(exc).__name__}: {exc}"}}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
