"""cortex.session.hooks — IDE-hook installer system for the Observed mode.

Phase 03 (T3.6–T3.10) of the Pluggable Middle architecture introduces
*Observed mode*: the user works with their IDE of choice, and an IDE
hook automatically emits ``cortex session checkpoint`` events so that
the documenter can later reconstruct context from a session enriched
with real-world activity.

Public API:
    :class:`HookAdapter`     — Protocol every IDE adapter implements.
    :class:`HookInstaller`   — orchestrator with a registry of adapters.
    :class:`InstallResult`   — outcome of an install operation.
    :class:`UninstallResult` — outcome of an uninstall operation.
    :class:`HookStatus`      — current installed/not-installed state.
    :func:`default_installer` — factory that wires the bundled adapters
                                (Claude Code, Cursor, Pi).

The installer NEVER writes outside ``target_dir`` (project root or user
config dir, depending on the caller's choice). All operations are
designed to be safe to re-run: ``install`` is idempotent, ``uninstall``
is a no-op if nothing is installed.
"""

from __future__ import annotations

from cortex.session.hooks.installer import (
    HookAdapter,
    HookInstaller,
    HookStatus,
    InstallResult,
    UninstallResult,
    default_installer,
)

__all__ = [
    "HookAdapter",
    "HookInstaller",
    "HookStatus",
    "InstallResult",
    "UninstallResult",
    "default_installer",
]
