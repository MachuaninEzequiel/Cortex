from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any


def slugify(value: str, *, fallback: str = "default") -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower()).strip("-")
    return normalized or fallback


def detect_git_branch(project_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        branch = result.stdout.strip()
        if result.returncode == 0 and branch:
            return branch
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "no-git-branch"


def resolve_episodic_persist_dir(project_root: Path, episodic_cfg: dict[str, Any]) -> Path:
    base_dir = episodic_cfg.get("persist_dir", ".memory/chroma")
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

