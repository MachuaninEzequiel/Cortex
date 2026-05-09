"""cortex.autopilot.hooks.session_finish — Emit session-finish payload for the IDE harness.

This module is designed to be called as a script or via ``python -m``.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cortex.autopilot.adapters.platform_detect import detect_platform
from cortex.autopilot.service import AutopilotService


def emit(project_root: str | Path, session_id: str | None = None) -> str:
    """Emit the session-finish JSON for the detected platform.

    Args:
        project_root: Path to the project root.
        session_id: Optional explicit session ID.

    Returns:
        JSON string with finish status.
    """
    root = Path(project_root)
    svc = AutopilotService.from_project_root(root)

    status = svc.status(session_id)
    if not status.active or status.state is None:
        return json.dumps({"error": "No active Autopilot session"})

    result = {
        "event": "SessionFinish",
        "session_id": status.state.session_id,
        "status": status.state.status,
        "mode": status.state.mode,
        "platform": detect_platform().value,
        "checkpoints": len(status.state.checkpoints),
    }
    return json.dumps(result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit Autopilot session-finish hook")
    parser.add_argument("--project-root", required=True, help="Project root path")
    parser.add_argument("--session-id", default=None, help="Explicit session ID")
    args = parser.parse_args(argv)

    try:
        print(emit(args.project_root, args.session_id))
        return 0
    except Exception as exc:
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
