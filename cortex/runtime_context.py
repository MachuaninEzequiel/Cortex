from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any


def slugify(value: str, *, fallback: str = "default") -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower()).strip("-")
    return normalized or fallback


def _run_git_command(project_root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    output = result.stdout.strip()
    if result.returncode != 0 or not output:
        return None
    return output


def detect_git_branch(project_root: Path) -> str:
    branch = _run_git_command(project_root, "rev-parse", "--abbrev-ref", "HEAD")
    return branch or "no-git-branch"


def detect_git_repo_path(project_root: Path) -> Path:
    repo_root = _run_git_command(project_root, "rev-parse", "--show-toplevel")
    if repo_root:
        return Path(repo_root).resolve()
    return project_root.resolve()


def resolve_episodic_persist_dir(project_root: Path, episodic_cfg: dict[str, Any]) -> Path:
    base_dir = episodic_cfg.get("persist_dir", "memory")
    mode = str(episodic_cfg.get("namespace_mode", "project")).strip().lower()
    namespace_value = str(episodic_cfg.get("namespace_value", "")).strip()

    resolved = (project_root / base_dir).resolve()
    if mode == "branch":
        branch = slugify(detect_git_branch(project_root), fallback="detached")
        return resolved / "branches" / branch
    if mode == "custom":
        if not namespace_value:
            namespace_value = "default"
        return resolved / "custom" / slugify(namespace_value)
    return resolved
