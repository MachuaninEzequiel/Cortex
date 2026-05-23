"""cortex.session.hooks.adapters.cursor — Git post-commit hook adapter.

Despite the name, this adapter is **not** Cursor-specific. It installs
into ``.git/hooks/post-commit`` and therefore works for any IDE that
ends up running ``git commit`` — Cursor, VSCode (Cline/Roo/Continue),
plain editors, the terminal. We call it ``cursor`` because Cursor is
the primary target documented in the Pluggable Middle architecture
(§10.5 / Phase 03 §3.3).

The hook fires after every commit and emits a checkpoint with the SHA
and subject of the new commit. The ``|| true`` clause guarantees that a
Cortex failure (e.g. ``cortex`` not on PATH, no active session) never
turns a successful commit into a failed one.

The hook block is delimited by sentinel markers so install / uninstall
do not clobber any pre-existing user content. If the user has their own
``post-commit`` script, the adapter appends a separate block; uninstall
removes only that block.
"""

from __future__ import annotations

import stat
from pathlib import Path

from cortex.session.hooks.installer import (
    HookStatus,
    InstallResult,
    UninstallResult,
)

POST_COMMIT_RELATIVE = Path(".git/hooks/post-commit")
START_MARKER = "# >>> cortex-session-hook (managed by `cortex session hooks`) >>>"
END_MARKER = "# <<< cortex-session-hook <<<"
SHEBANG = "#!/bin/sh"

HOOK_BLOCK = "\n".join(
    [
        START_MARKER,
        "# Emits a checkpoint to the active Cortex session after each commit.",
        "# The `|| true` guard prevents a Cortex failure from blocking commits.",
        "SHA=$(git rev-parse --short HEAD 2>/dev/null) || SHA=unknown",
        "SUBJ=$(git log -1 --pretty=%s 2>/dev/null) || SUBJ='(no subject)'",
        "cortex session checkpoint --source ide-hook "
        '--note "git commit ${SHA}: ${SUBJ}" >/dev/null 2>&1 || true',
        END_MARKER,
        "",
    ]
)


class CursorGitHookAdapter:
    """Manage the Cortex block inside ``.git/hooks/post-commit``."""

    name = "cursor"

    def is_supported(self) -> bool:
        # Git is essentially universal in software-engineering workflows;
        # the actual ``.git/`` directory check happens at install time.
        return True

    # ── Public API ─────────────────────────────────────────────────

    def install(self, target_dir: Path) -> InstallResult:
        target = self._hook_path(target_dir)
        self._require_git_repo(target_dir)
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
        self._ensure_executable(target)
        return InstallResult(
            ide=self.name,
            installed=True,
            modified_paths=[target],
            message=f"installed git post-commit hook in {target}",
        )

    def uninstall(self, target_dir: Path) -> UninstallResult:
        target = self._hook_path(target_dir)
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
        if cleaned.strip() in {"", SHEBANG}:
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
        target = self._hook_path(target_dir)
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
    def _hook_path(target_dir: Path) -> Path:
        return Path(target_dir) / POST_COMMIT_RELATIVE

    @staticmethod
    def _require_git_repo(target_dir: Path) -> None:
        git_dir = Path(target_dir) / ".git"
        if not git_dir.exists():
            raise ValueError(
                f"not a git repository: {git_dir} does not exist (run `git init` first)"
            )

    @staticmethod
    def _read(path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    @staticmethod
    def _render(existing: str) -> str:
        """Produce the new file contents, preserving user content if any."""
        existing = existing.rstrip()
        if not existing:
            return SHEBANG + "\n\n" + HOOK_BLOCK
        if not existing.lstrip().startswith("#!"):
            # No shebang in user file; add one for safety.
            return SHEBANG + "\n" + existing + "\n\n" + HOOK_BLOCK
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

    @staticmethod
    def _ensure_executable(path: Path) -> None:
        try:
            mode = path.stat().st_mode
            path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except OSError:
            # Windows / read-only filesystems: chmod has no meaning. The git
            # hook is invoked by git via the shell, which does not need the
            # POSIX executable bit on Windows.
            pass


__all__ = ["CursorGitHookAdapter", "START_MARKER", "END_MARKER", "HOOK_BLOCK"]
