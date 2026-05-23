"""cortex.session.hooks.adapters.opencode — opencode IDE hook adapter.

Installs a Cortex-managed entry into ``.opencode/hooks.md`` (project
scope) so that opencode emits a checkpoint to the active Cortex session
on every file-edit event. The hook block is delimited by HTML-comment
sentinel markers so install / uninstall preserve user content.

Format research is captured in
``docs/pluggable-middle/fases/_internal/opencode-hooks-research.md``.
"""

from __future__ import annotations

from pathlib import Path

from cortex.session.hooks.installer import (
    HookStatus,
    InstallResult,
    UninstallResult,
)

HOOKS_RELATIVE = Path(".opencode/hooks.md")
START_MARKER = "<!-- >>> cortex-session-hook (managed by 'cortex session hooks') >>> -->"
END_MARKER = "<!-- <<< cortex-session-hook <<< -->"

_HOOK_COMMAND = (
    "cortex session checkpoint --source ide-hook "
    '--note "edit via opencode" >/dev/null 2>&1 || true'
)

HOOK_BLOCK = "\n".join(
    [
        START_MARKER,
        "## Cortex session checkpoint",
        "",
        "Emits a checkpoint to the active Cortex session after each",
        "significant edit. The ``|| true`` guard prevents Cortex failures",
        "from interrupting opencode.",
        "",
        "```sh",
        _HOOK_COMMAND,
        "```",
        END_MARKER,
        "",
    ]
)


class OpencodeHookAdapter:
    """Manage the Cortex block inside ``.opencode/hooks.md``."""

    name = "opencode"

    def is_supported(self) -> bool:
        # The adapter only touches a markdown file; the opencode binary
        # need not be installed for install/uninstall/status to work.
        return True

    # ── Public API ─────────────────────────────────────────────────

    def install(self, target_dir: Path) -> InstallResult:
        target = self._hooks_path(target_dir)
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
            message=f"installed opencode hooks entry in {target}",
        )

    def uninstall(self, target_dir: Path) -> UninstallResult:
        target = self._hooks_path(target_dir)
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
            message=f"removed cortex block from {target}",
        )

    def status(self, target_dir: Path) -> HookStatus:
        target = self._hooks_path(target_dir)
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
                f"cortex block present in {target}"
                if installed
                else f"{target} exists but no cortex block"
            ),
        )

    # ── Internals ─────────────────────────────────────────────────

    @staticmethod
    def _hooks_path(target_dir: Path) -> Path:
        return Path(target_dir) / HOOKS_RELATIVE

    @staticmethod
    def _read(path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    @staticmethod
    def _render(existing: str) -> str:
        """Build the new file content, preserving user-authored sections."""
        existing = existing.rstrip()
        if not existing:
            return HOOK_BLOCK
        return existing + "\n\n" + HOOK_BLOCK

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


__all__ = [
    "OpencodeHookAdapter",
    "HOOK_BLOCK",
    "START_MARKER",
    "END_MARKER",
    "HOOKS_RELATIVE",
]
