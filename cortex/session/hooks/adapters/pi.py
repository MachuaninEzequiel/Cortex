"""cortex.session.hooks.adapters.pi — Pi Coding Agent hook adapter.

Pi exposes its automation via a project-local ``justfile`` (the Pi
runtime invokes ``just <recipe>`` for routine tasks). This adapter adds
two recipes to the project ``justfile`` so Pi flows can:

    just cortex-checkpoint NOTE     — emit a checkpoint to the active session
    just cortex-finish               — run cortex finish-session

The recipes are wrapped in sentinel markers so install / uninstall are
precise even when the user has their own ``justfile`` content.

Target file: ``<target_dir>/justfile`` (created if absent).
"""

from __future__ import annotations

from pathlib import Path

from cortex.session.hooks.installer import (
    HookStatus,
    InstallResult,
    UninstallResult,
)

JUSTFILE_RELATIVE = Path("justfile")
START_MARKER = "# >>> cortex-session-hook (managed by `cortex session hooks`) >>>"
END_MARKER = "# <<< cortex-session-hook <<<"

RECIPE_BLOCK = "\n".join(
    [
        START_MARKER,
        "# Recipes invoked by Pi Coding Agent (or any just user) to enrich the",
        "# active Cortex session. All recipes use `|| true` so a Cortex failure",
        "# never aborts the surrounding Pi pipeline.",
        "",
        "cortex-checkpoint NOTE='pi checkpoint':",
        '    cortex session checkpoint --source ide-hook --note "{{NOTE}}" >/dev/null 2>&1 || true',
        "",
        "cortex-finish:",
        "    cortex finish-session || true",
        "",
        "cortex-status:",
        "    cortex session show || true",
        END_MARKER,
        "",
    ]
)


class PiHookAdapter:
    """Manage the Cortex recipe block inside ``<target_dir>/justfile``."""

    name = "pi"

    def is_supported(self) -> bool:
        # The adapter manages a text file; whether ``just`` is on PATH is
        # the user's concern at invocation time, not at install time.
        return True

    # ── Public API ─────────────────────────────────────────────────

    def install(self, target_dir: Path) -> InstallResult:
        target = self._justfile_path(target_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        existing = self._read(target)
        if START_MARKER in existing:
            return InstallResult(
                ide=self.name,
                installed=True,
                modified_paths=[],
                message=f"already installed in {target}",
            )
        new_content = self._render(existing)
        target.write_text(new_content, encoding="utf-8", newline="\n")
        return InstallResult(
            ide=self.name,
            installed=True,
            modified_paths=[target],
            message=f"installed cortex recipes in {target}",
        )

    def uninstall(self, target_dir: Path) -> UninstallResult:
        target = self._justfile_path(target_dir)
        if not target.exists():
            return UninstallResult(
                ide=self.name,
                uninstalled=False,
                removed_paths=[],
                message=f"{target} does not exist",
            )
        content = self._read(target)
        if START_MARKER not in content:
            return UninstallResult(
                ide=self.name,
                uninstalled=False,
                removed_paths=[],
                message=f"no cortex-managed block in {target}",
            )
        cleaned = self._strip_block(content).rstrip() + "\n"
        if cleaned.strip() == "":
            target.unlink()
            return UninstallResult(
                ide=self.name,
                uninstalled=True,
                removed_paths=[target],
                message=f"removed (file had no other content) {target}",
            )
        target.write_text(cleaned, encoding="utf-8", newline="\n")
        return UninstallResult(
            ide=self.name,
            uninstalled=True,
            removed_paths=[target],
            message=f"removed cortex recipes from {target}",
        )

    def status(self, target_dir: Path) -> HookStatus:
        target = self._justfile_path(target_dir)
        if not target.exists():
            return HookStatus(
                ide=self.name,
                installed=False,
                detail=f"{target} does not exist",
            )
        installed = START_MARKER in self._read(target)
        return HookStatus(
            ide=self.name,
            installed=installed,
            detail=(
                f"cortex recipes present in {target}"
                if installed
                else f"{target} exists but no cortex recipes"
            ),
        )

    # ── Internals ─────────────────────────────────────────────────

    @staticmethod
    def _justfile_path(target_dir: Path) -> Path:
        return Path(target_dir) / JUSTFILE_RELATIVE

    @staticmethod
    def _read(path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    @staticmethod
    def _render(existing: str) -> str:
        existing = existing.rstrip()
        if not existing:
            return RECIPE_BLOCK
        return existing + "\n\n" + RECIPE_BLOCK

    @staticmethod
    def _strip_block(content: str) -> str:
        kept: list[str] = []
        in_block = False
        for line in content.splitlines(keepends=True):
            stripped = line.rstrip("\n")
            if stripped == START_MARKER:
                in_block = True
                continue
            if stripped == END_MARKER:
                in_block = False
                continue
            if not in_block:
                kept.append(line)
        return "".join(kept)


__all__ = ["PiHookAdapter", "RECIPE_BLOCK", "START_MARKER", "END_MARKER"]
