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
    # Codex aliases — kept short because users type them frequently.
    "openai-codex": "codex",
    "codex-cli": "codex",
}

# IDEs officially targeted by Cortex (full support + onboarding docs).
# These are the IDEs an adopter is expected to use; everything else is
# best-effort community support.
TARGET_IDES: frozenset[str] = frozenset({"claude_code", "opencode", "pi", "codex"})

# Experimental adapters: shipped but not yet recommended for adopters.
_EXPERIMENTAL_IDES = {"antigravity", "hermes", "zed"}

# Community adapters: stable but not part of the official target matrix.
# Surfaced in CLI listings only when explicitly requested.
COMMUNITY_IDES: frozenset[str] = frozenset({"cursor", "claude_desktop", "vscode", "windsurf"})


def _build_registry() -> dict[str, type[IDEAdapter]]:
    """Import and register all known adapters."""
    from cortex.ide.adapters.antigravity import AntigravityAdapter
    from cortex.ide.adapters.claude_code import ClaudeCodeAdapter
    from cortex.ide.adapters.claude_desktop import ClaudeDesktopAdapter
    from cortex.ide.adapters.codex import CodexAdapter
    from cortex.ide.adapters.cursor import CursorAdapter
    from cortex.ide.adapters.hermes import HermesAdapter
    from cortex.ide.adapters.opencode import OpenCodeAdapter
    from cortex.ide.adapters.vscode import VSCodeAdapter
    from cortex.ide.adapters.windsurf import WindsurfAdapter
    from cortex.ide.adapters.zed import ZedAdapter
    from cortex.ide.adapters.pi import PiAdapter

    registry: dict[str, type[IDEAdapter]] = {}
    for adapter_cls in (
        # Target IDEs first — order they appear in CLI listings.
        ClaudeCodeAdapter,
        OpenCodeAdapter,
        PiAdapter,
        CodexAdapter,
        # Community adapters.
        CursorAdapter,
        ClaudeDesktopAdapter,
        VSCodeAdapter,
        WindsurfAdapter,
        # Experimental adapters.
        ZedAdapter,
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
        target = ", ".join(sorted(TARGET_IDES))
        community = ", ".join(sorted(COMMUNITY_IDES))
        experimental = ", ".join(sorted(_EXPERIMENTAL_IDES))
        raise KeyError(
            f"Unknown IDE: '{ide_name}'.\n"
            f"  Target (officially supported): {target}\n"
            f"  Community (best-effort):       {community}\n"
            f"  Experimental:                  {experimental}"
        )

    return registry[normalized]()


def get_all_adapters(*, include_experimental: bool = False) -> list[IDEAdapter]:
    """Return instances of registered adapters."""
    registry = get_registry()
    names = sorted(registry.keys())
    if not include_experimental:
        names = [name for name in names if name not in _EXPERIMENTAL_IDES]
    return [registry[name]() for name in names]


def get_supported_ides(*, include_experimental: bool = False) -> list[str]:
    """Return sorted list of IDE names intended for user-facing selection."""
    names = sorted(get_registry().keys())
    if not include_experimental:
        names = [name for name in names if name not in _EXPERIMENTAL_IDES]
    return names


def get_target_ides() -> list[str]:
    """Return the IDEs officially targeted by Cortex (Claude Code, OpenCode, Pi, Codex)."""
    registry = get_registry()
    return sorted(name for name in registry if name in TARGET_IDES)


def get_ide_tier(ide_name: str) -> str:
    """Classify an IDE as ``target | community | experimental``.

    Raises ``KeyError`` if the IDE is not registered.
    """
    normalized = _ALIASES.get(ide_name.lower().strip(), ide_name.lower().strip())
    if normalized not in get_registry():
        raise KeyError(f"Unknown IDE: '{ide_name}'")
    if normalized in TARGET_IDES:
        return "target"
    if normalized in _EXPERIMENTAL_IDES:
        return "experimental"
    return "community"
