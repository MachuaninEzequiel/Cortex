"""cortex.session.hooks.installer — Generic hook installer infrastructure.

This module defines the contract every IDE-specific hook adapter must
satisfy, plus the orchestrator (:class:`HookInstaller`) that the CLI
talks to.

Each adapter is responsible for:

* Detecting whether its target IDE/runtime is supported on the current
  system (so the installer can present a useful ``list`` to the user).
* Installing a small, IDE-native artifact that, when triggered by an
  IDE event (file save, post-commit, etc.), invokes the
  ``cortex session checkpoint --source ide-hook ...`` CLI command.
* Removing that artifact cleanly on ``uninstall``.
* Reporting current status (installed / not installed) for the doctor.

The contract is intentionally narrow. Anything more complex than a
trigger script lives outside this layer.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class InstallResult:
    """Outcome of :meth:`HookInstaller.install` / :meth:`HookAdapter.install`."""

    ide: str
    installed: bool
    modified_paths: list[Path] = field(default_factory=list)
    message: str = ""


@dataclass(frozen=True)
class UninstallResult:
    """Outcome of :meth:`HookInstaller.uninstall` / :meth:`HookAdapter.uninstall`."""

    ide: str
    uninstalled: bool
    removed_paths: list[Path] = field(default_factory=list)
    message: str = ""


@dataclass(frozen=True)
class HookStatus:
    """Current installation state of an adapter under a target directory."""

    ide: str
    installed: bool
    supported: bool = True
    detail: str = ""


@runtime_checkable
class HookAdapter(Protocol):
    """Protocol every IDE-specific adapter must implement.

    ``target_dir`` is interpreted by each adapter (typically the project
    root for project-scoped hooks; the user home for user-scoped ones).

    Adapters never raise on benign conditions: if ``install`` is called
    twice, the second call should detect the existing install and return
    ``installed=True`` with a clear ``message``. Hard failures (e.g.
    cannot write to the target directory) DO raise.
    """

    name: str

    def is_supported(self) -> bool:
        """Whether this adapter can run on the current machine.

        For adapters that always work (e.g. git hooks) returns True
        unconditionally. For adapters that need a specific binary or
        environment (Pi, Claude Code's CLI) returns False when the
        prerequisite is absent.
        """
        ...

    def install(self, target_dir: Path) -> InstallResult:
        """Install the hook artifact inside ``target_dir``."""
        ...

    def uninstall(self, target_dir: Path) -> UninstallResult:
        """Remove the hook artifact from ``target_dir``."""
        ...

    def status(self, target_dir: Path) -> HookStatus:
        """Report whether the hook is currently installed under ``target_dir``."""
        ...


class HookInstaller:
    """Registry + dispatcher for :class:`HookAdapter` instances.

    Stateless beyond its adapter map. The CLI builds one of these via
    :func:`default_installer` and calls install / uninstall / status by
    IDE name.
    """

    def __init__(self, adapters: Iterable[HookAdapter] | dict[str, HookAdapter]) -> None:
        if isinstance(adapters, dict):
            self._adapters: dict[str, HookAdapter] = dict(adapters)
        else:
            self._adapters = {a.name: a for a in adapters}

    # ── Read API ────────────────────────────────────────────────

    def list_available_adapters(self) -> list[str]:
        """Names of every adapter known to this installer (sorted)."""
        return sorted(self._adapters)

    def list_supported(self) -> list[str]:
        """Names of adapters whose ``is_supported()`` returns True (sorted)."""
        return sorted(name for name, a in self._adapters.items() if a.is_supported())

    def get(self, ide: str) -> HookAdapter:
        """Return the adapter registered under ``ide`` or raise :class:`KeyError`."""
        try:
            return self._adapters[ide]
        except KeyError as exc:
            valid = ", ".join(self.list_available_adapters())
            raise KeyError(f"unknown IDE adapter {ide!r}; available: {valid}") from exc

    # ── Write API ───────────────────────────────────────────────

    def install(self, ide: str, target_dir: Path) -> InstallResult:
        """Install the ``ide`` hook under ``target_dir``."""
        adapter = self.get(ide)
        return adapter.install(Path(target_dir))

    def uninstall(self, ide: str, target_dir: Path) -> UninstallResult:
        """Uninstall the ``ide`` hook from ``target_dir``."""
        adapter = self.get(ide)
        return adapter.uninstall(Path(target_dir))

    def status(self, ide: str, target_dir: Path) -> HookStatus:
        """Report the current status of the ``ide`` hook under ``target_dir``."""
        adapter = self.get(ide)
        return adapter.status(Path(target_dir))

    def status_all(self, target_dir: Path) -> list[HookStatus]:
        """Status of every known adapter (sorted by name)."""
        return [
            self._adapters[name].status(Path(target_dir)) for name in self.list_available_adapters()
        ]


def default_installer() -> HookInstaller:
    """Build the installer with the bundled adapters.

    Pluggable Middle Phase 03 shipped 3 (Claude Code, Cursor, Pi);
    Phase 05 added opencode. Import is lazy so a broken third-party
    adapter in the same package cannot bring down ``cortex session``
    for the supported IDEs.
    """
    from cortex.session.hooks.adapters.claude_code import ClaudeCodeHookAdapter
    from cortex.session.hooks.adapters.cursor import CursorGitHookAdapter
    from cortex.session.hooks.adapters.opencode import OpencodeHookAdapter
    from cortex.session.hooks.adapters.pi import PiHookAdapter

    return HookInstaller(
        [
            ClaudeCodeHookAdapter(),
            CursorGitHookAdapter(),
            OpencodeHookAdapter(),
            PiHookAdapter(),
        ]
    )


__all__ = [
    "HookAdapter",
    "HookInstaller",
    "HookStatus",
    "InstallResult",
    "UninstallResult",
    "default_installer",
]
