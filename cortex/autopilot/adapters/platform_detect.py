"""cortex.autopilot.adapters.platform_detect — Detect IDE harness at runtime."""
from __future__ import annotations

import os
from enum import Enum


class Platform(Enum):
    CLAUDE_CODE = "claude-code"
    CURSOR = "cursor"
    COPILOT_CLI = "copilot-cli"
    OPENCODE = "opencode"
    CODEX = "codex"
    PI = "pi"
    UNKNOWN = "unknown"


def detect_platform() -> Platform:
    """Detect the active IDE harness from environment variables."""
    if os.environ.get("CURSOR_PLUGIN_ROOT"):
        return Platform.CURSOR
    if os.environ.get("CLAUDE_PLUGIN_ROOT") and not os.environ.get("COPILOT_CLI"):
        return Platform.CLAUDE_CODE
    if os.environ.get("COPILOT_CLI"):
        return Platform.COPILOT_CLI
    if os.environ.get("OPENCODE_PLUGIN_ROOT"):
        return Platform.OPENCODE
    if os.environ.get("CODEX_PLUGIN_ROOT"):
        return Platform.CODEX
    if os.environ.get("PI_PLUGIN_ROOT"):
        return Platform.PI
    if os.environ.get("PI_CODING_AGENT"):
        return Platform.PI
    return Platform.UNKNOWN
