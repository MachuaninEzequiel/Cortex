"""
cortex.ide.registry
-------------------
Auto-discovery and registration of IDE adapters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.ide.base import IDEAdapter

_registry: dict[str, type[IDEAdapter]] | None = None

_ALIASES = {
    "claude": "claude_code",
    "claude-code": "claude_code",
    "claude-desktop": "claude_desktop",
    "code": "vscode",
    "visual-studio-code": "vscode",
    "vs-code": "vscode",
}


def _build_registry() -> dict[str, type[IDEAdapter]]:
    """Import and register all known adapters."""
    from cortex.ide.adapters.antigravity import AntigravityAdapter
    from cortex.ide.adapters.claude_code import ClaudeCodeAdapter
    from cortex.ide.adapters.claude_desktop import ClaudeDesktopAdapter
    from cortex.ide.adapters.cursor import CursorAdapter
    from cortex.ide.adapters.hermes import HermesAdapter
    from cortex.ide.adapters.opencode import OpenCodeAdapter
    from cortex.ide.adapters.vscode import VSCodeAdapter
    from cortex.ide.adapters.windsurf import WindsurfAdapter
    from cortex.ide.adapters.zed import ZedAdapter

    registry: dict[str, type[IDEAdapter]] = {}
    for adapter_cls in (
        OpenCodeAdapter,
        CursorAdapter,
        ClaudeCodeAdapter,
        ClaudeDesktopAdapter,
        VSCodeAdapter,
        ZedAdapter,
        WindsurfAdapter,
        AntigravityAdapter,
        HermesAdapter,
    ):
        instance = adapter_cls()
        registry[instance.name] = adapter_cls

    return registry


def get_registry() -> dict[str, type[IDEAdapter]]:
    """Return the adapter registry, building it on first call."""
    global _registry
    if _registry is None:
        _registry = _build_registry()
    return _registry


def get_adapter(ide_name: str) -> IDEAdapter:
    """Get an adapter instance by IDE name."""
    registry = get_registry()
    normalized = ide_name.lower().strip()
    normalized = _ALIASES.get(normalized, normalized)

    if normalized not in registry:
        available = ", ".join(sorted(registry.keys()))
        raise KeyError(f"Unknown IDE: '{ide_name}'. Available: {available}")

    return registry[normalized]()


def get_all_adapters() -> list[IDEAdapter]:
    """Return instances of all registered adapters."""
    registry = get_registry()
    return [cls() for cls in registry.values()]


def get_supported_ides() -> list[str]:
    """Return sorted list of supported IDE names."""
    return sorted(get_registry().keys())
