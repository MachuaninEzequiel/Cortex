"""
cortex.security.paths
---------------------
Centralised path-safety helpers for Cortex.

Every component that builds filesystem paths from operational input
should use these helpers instead of ad-hoc string concatenation.
"""

from __future__ import annotations

from pathlib import Path


class PathSecurityError(ValueError):
    """Raised when a path escapes the allowed root directory."""


def resolve_safe(root: Path, rel: str | Path) -> Path:
    """Resolve *rel* under *root* and enforce that the result stays inside *root*.

    Args:
        root: Absolute base directory that must not be escaped.
        rel: Relative path to resolve.  Absolute paths are rejected.

    Returns:
        Fully-resolved path guaranteed to be inside *root*.

    Raises:
        PathSecurityError: If *rel* is absolute or resolves outside *root*.
    """
    root_resolved = root.resolve()
    rel_path = Path(rel)
    if rel_path.is_absolute():
        raise PathSecurityError(f"Absolute paths are not allowed: {rel}")
    target = (root_resolved / rel_path).resolve()
    try:
        target.relative_to(root_resolved)
    except ValueError as exc:
        raise PathSecurityError(f"Path escapes allowed root ({root}): {rel}") from exc
    return target


def validate_under_root(path: Path, root: Path) -> Path:
    """Validate that an already-constructed *path* stays inside *root*.

    Args:
        path: Path to validate (may be absolute or relative).
        root: Allowed root directory.

    Returns:
        Fully-resolved path guaranteed to be inside *root*.

    Raises:
        PathSecurityError: If *path* resolves outside *root*.
    """
    root_resolved = root.resolve()
    target = path.resolve()
    try:
        target.relative_to(root_resolved)
    except ValueError as exc:
        raise PathSecurityError(f"Path escapes allowed root ({root}): {path}") from exc
    return target
