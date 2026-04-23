"""
cortex.ide
----------
IDE adapter layer for Cortex agent profile injection.

Provides a unified interface for injecting Cortex agent profiles and MCP
configuration across all supported IDEs. Each IDE has its own adapter that
implements the common IDEAdapter contract.

Usage::

    from cortex.ide import inject, inject_all, uninstall, get_supported_ides

    inject("cursor", project_root=Path.cwd())
    inject_all(project_root=Path.cwd())
    uninstall("cursor")
    print(get_supported_ides())
"""

from __future__ import annotations

from pathlib import Path

from cortex.ide.prompts import build_all_prompts, build_cursor_prompts
from cortex.ide.registry import get_adapter, get_all_adapters, get_supported_ides

__all__ = ["inject", "inject_all", "uninstall", "uninstall_all", "get_supported_ides"]


def inject(ide_name: str, project_root: Path | None = None) -> list[str]:
    """Inject Cortex profiles and MCP config into a specific IDE."""
    if project_root is None:
        project_root = _find_project_root()

    adapter = get_adapter(ide_name)
    
    # Use Cursor-specific prompts for Cursor IDE
    if ide_name == "cursor":
        prompts = build_cursor_prompts(project_root)
    else:
        prompts = build_all_prompts(project_root)

    print(f"[Cortex IDE] Injecting profiles for {adapter.display_name}...")
    files = adapter.inject_all(project_root, prompts)

    for f in files:
        print(f"  [OK] {f}")

    return files


def inject_all(project_root: Path | None = None) -> dict[str, list[str]]:
    """Inject Cortex profiles into all supported IDEs."""
    if project_root is None:
        project_root = _find_project_root()

    prompts = build_all_prompts(project_root)
    results: dict[str, list[str]] = {}

    print("[Cortex IDE] Injecting profiles for all supported IDEs...")
    for adapter in get_all_adapters():
        try:
            files = adapter.inject_all(project_root, prompts)
            results[adapter.name] = files
            for f in files:
                print(f"  [{adapter.display_name}] {f}")
        except Exception as exc:
            print(f"  [{adapter.display_name}] ERROR: {exc}")
            results[adapter.name] = []

    print(f"[Cortex IDE] Done. Configured {len([v for v in results.values() if v])} IDEs.")
    return results


def uninstall(ide_name: str) -> list[str]:
    """Remove Cortex profiles and MCP config from a specific IDE."""
    adapter = get_adapter(ide_name)
    print(f"[Cortex IDE] Removing Cortex from {adapter.display_name}...")
    files = adapter.uninstall()

    if files:
        for f in files:
            print(f"  [REMOVED] {f}")
    else:
        print("  [INFO] No managed Cortex files were removed.")

    return files


def uninstall_all() -> dict[str, list[str]]:
    """Remove Cortex profiles and MCP config from every supported IDE."""
    results: dict[str, list[str]] = {}

    print("[Cortex IDE] Removing Cortex from all supported IDEs...")
    for adapter in get_all_adapters():
        try:
            files = adapter.uninstall()
            results[adapter.name] = files
            if files:
                for f in files:
                    print(f"  [{adapter.display_name}] removed {f}")
            else:
                print(f"  [{adapter.display_name}] nothing to remove")
        except Exception as exc:
            print(f"  [{adapter.display_name}] ERROR: {exc}")
            results[adapter.name] = []

    return results


def _find_project_root() -> Path:
    """Find the Cortex project root by looking for .cortex directory."""
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / ".cortex").exists():
            return parent
    raise FileNotFoundError(
        "Could not find .cortex directory. Are you in a Cortex project? "
        "Run `cortex setup agent` first."
    )
