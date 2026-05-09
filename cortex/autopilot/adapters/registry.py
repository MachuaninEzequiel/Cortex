"""cortex.autopilot.adapters.registry — Adapter registry and lookup."""
from __future__ import annotations

from typing import TypeVar

from cortex.autopilot.adapters.claude_code import ClaudeCodeAutopilotAdapter
from cortex.autopilot.adapters.codex import CodexPluginAutopilotAdapter
from cortex.autopilot.adapters.cursor import CursorAutopilotAdapter
from cortex.autopilot.adapters.opencode import OpenCodeAutopilotAdapter
from cortex.autopilot.adapters.platform_detect import Platform, detect_platform

T = TypeVar("T")

_ADAPTERS: dict[str, type] = {
    "cursor": CursorAutopilotAdapter,
    "claude-code": ClaudeCodeAutopilotAdapter,
    "opencode": OpenCodeAutopilotAdapter,
    "codex": CodexPluginAutopilotAdapter,
}


def get_adapter(name: str) -> type:
    """Return the adapter class for *name* or raise KeyError."""
    if name not in _ADAPTERS:
        raise KeyError(f"Unknown adapter: {name}. Available: {list(_ADAPTERS)}")
    return _ADAPTERS[name]


def list_adapters() -> list[str]:
    """Return sorted list of registered adapter names."""
    return sorted(_ADAPTERS)


def get_adapter_for_current_platform() -> type | None:
    """Return the adapter matching the current platform, or None."""
    platform = detect_platform()
    if platform == Platform.UNKNOWN:
        return None
    return _ADAPTERS.get(platform.value)
