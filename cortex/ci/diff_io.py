"""cortex.ci.diff_io — Resolve the diff text from CLI inputs.

Three input modes, in priority order:

1. ``--diff <file>``: read raw text from the file.
2. ``--base-commit`` + ``--head-commit``: run ``git diff base..head``.
3. Auto: ``git diff <trunk>..HEAD`` where trunk is ``main`` or
   ``master`` (whichever exists).
"""

from __future__ import annotations

from pathlib import Path

from cortex.session import git as git_module


class DiffResolutionError(Exception):
    """Raised when the caller asked for a diff that cannot be produced."""


def read_diff_from_args(
    *,
    diff_file: Path | None,
    base_commit: str | None,
    head_commit: str | None,
    repo_root: Path,
) -> str:
    """Return the diff text, falling through the three input modes."""
    if diff_file is not None:
        path = Path(diff_file)
        if not path.is_file():
            raise DiffResolutionError(f"--diff file not found: {path}")
        return path.read_text(encoding="utf-8", errors="replace")

    if base_commit and head_commit:
        try:
            return git_module.diff(base_commit, head_commit, repo_root)
        except Exception as exc:  # noqa: BLE001
            raise DiffResolutionError(
                f"git diff {base_commit[:8]}..{head_commit[:8]} failed: {exc}"
            ) from exc

    if base_commit and not head_commit:
        try:
            return git_module.diff(base_commit, "HEAD", repo_root)
        except Exception as exc:  # noqa: BLE001
            raise DiffResolutionError(
                f"git diff {base_commit[:8]}..HEAD failed: {exc}"
            ) from exc

    # Auto-detect trunk.
    trunk = _detect_trunk(repo_root)
    if trunk is None:
        raise DiffResolutionError(
            "could not auto-detect trunk branch (neither 'main' nor 'master' exists); "
            "pass --diff / --base-commit / --head-commit explicitly"
        )
    try:
        return git_module.diff(trunk, "HEAD", repo_root)
    except Exception as exc:  # noqa: BLE001
        raise DiffResolutionError(
            f"git diff {trunk}..HEAD failed: {exc}"
        ) from exc


def _detect_trunk(repo_root: Path) -> str | None:
    """Return ``main`` or ``master`` (whichever exists), or ``None``."""
    import subprocess

    for candidate in ("main", "master"):
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/heads/{candidate}"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return candidate
    return None


__all__ = ["DiffResolutionError", "read_diff_from_args"]
