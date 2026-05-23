"""cortex.session.git — Minimal subprocess wrappers for git commands.

We avoid GitPython (not a project dependency, ships ~MB of bytecode) and
shell out to ``git`` directly. The wrappers are intentionally small and
typed so the service layer can mock or replace them in tests.

All functions raise :class:`GitError` on subprocess failure, on a missing
``git`` executable, on a subprocess timeout, or on output that violates a
documented invariant (e.g. ``rev-parse HEAD`` not returning a full SHA-1).

For projects that lack a git repository entirely, callers should prefer
the ``try_*`` helpers and :func:`is_git_repo` over the strict wrappers —
those return ``None`` / ``False`` instead of raising so the service layer
can fall back to ``GITLESS_COMMIT_PLACEHOLDER`` and run in degraded mode.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_HEX_DIGITS = frozenset("0123456789abcdef")

# Default timeout for every git subprocess call. ``rev-parse HEAD`` normally
# returns in <100ms on a healthy repo; anything past 10s indicates a real
# problem (stale ``index.lock``, antivirus scan, credential helper waiting
# on a GUI prompt, network drive stall, ...). Without this guard a single
# stuck call would freeze the MCP server for minutes — see the May 2026
# incident with the ``realestate`` project inheriting a git repo from a
# parent directory.
_GIT_SUBPROCESS_TIMEOUT_SECONDS: float = 10.0


class GitError(Exception):
    """Raised on any failure of an underlying git command."""


def _run(args: list[str], repo_root: Path) -> str:
    """Run ``git <args>`` in *repo_root* and return stdout (text)."""
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(repo_root),
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_GIT_SUBPROCESS_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        raise GitError("git executable not found on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitError(
            f"git {' '.join(args)} timed out after "
            f"{_GIT_SUBPROCESS_TIMEOUT_SECONDS}s in {repo_root}"
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise GitError(f"git {' '.join(args)} failed (exit {exc.returncode}): {stderr}") from exc
    return proc.stdout


def is_git_repo(repo_root: Path) -> bool:
    """Return ``True`` iff *repo_root* is inside a git working tree.

    Uses ``git rev-parse --is-inside-work-tree``, which is the
    git-blessed way to detect a repo without depending on the presence
    of a literal ``.git`` directory (worktrees, submodules, and bare
    repos all answer correctly). Failures and timeouts return ``False``
    — callers should treat the workspace as gitless in that case.
    """
    try:
        out = _run(["rev-parse", "--is-inside-work-tree"], repo_root).strip()
    except GitError:
        return False
    return out == "true"


def get_head_commit(repo_root: Path) -> str:
    """Return the 40-char lowercase hex SHA-1 of HEAD."""
    sha = _run(["rev-parse", "HEAD"], repo_root).strip()
    if len(sha) != 40 or not set(sha).issubset(_HEX_DIGITS):
        raise GitError(f"git rev-parse HEAD returned unexpected output: {sha!r}")
    return sha


def try_get_head_commit(repo_root: Path) -> str | None:
    """Soft variant of :func:`get_head_commit` that returns ``None`` on failure.

    Use this from code paths that must degrade gracefully when the
    workspace lacks git (or git is otherwise unusable). The strict
    variant is preferred elsewhere because it surfaces real bugs
    instead of swallowing them.
    """
    try:
        return get_head_commit(repo_root)
    except GitError:
        return None


def get_current_branch(repo_root: Path) -> str:
    """Return the current branch name (or ``HEAD`` when detached)."""
    return _run(["rev-parse", "--abbrev-ref", "HEAD"], repo_root).strip()


def try_get_current_branch(repo_root: Path) -> str | None:
    """Soft variant of :func:`get_current_branch`."""
    try:
        return get_current_branch(repo_root)
    except GitError:
        return None


def diff(start_ref: str, end_ref: str, repo_root: Path) -> str:
    """Return ``git diff <start_ref>..<end_ref>`` stdout."""
    return _run(["diff", f"{start_ref}..{end_ref}"], repo_root)


def diff_name_status(start_ref: str, end_ref: str, repo_root: Path) -> str:
    """Return ``git diff --name-status <start_ref>..<end_ref>`` stdout.

    The output format is one entry per line, tab-separated:

        ``A\\t<path>``                              — Added
        ``M\\t<path>``                              — Modified
        ``D\\t<path>``                              — Deleted
        ``R<n>\\t<old_path>\\t<new_path>``          — Renamed (n = similarity %)
        ``C<n>\\t<src_path>\\t<dst_path>``          — Copied

    Used by the documenter to classify changes without full-diff parsing.
    """
    return _run(["diff", "--name-status", f"{start_ref}..{end_ref}"], repo_root)


__all__ = [
    "GitError",
    "diff",
    "diff_name_status",
    "get_current_branch",
    "get_head_commit",
    "is_git_repo",
    "try_get_current_branch",
    "try_get_head_commit",
]
