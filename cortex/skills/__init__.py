"""
cortex.skills
-------------
Bundled Qwen Code skills for Obsidian Markdown documentation.

These skills are installed into the project's .qwen/skills/ directory
during ``cortex setup`` so that AI agents working on the project know
how to write proper documentation.

Available skills
----------------
- obsidian-markdown — Obsidian Flavored Markdown (wikilinks, embeds, callouts, properties)
- json-canvas       — JSON Canvas format for visual note connections
- obsidian-bases    — Obsidian Bases for filtered/sorted note views
- obsidian-cli      — Obsidian CLI commands
- defuddle          — Web page cleanup and extraction
"""

from __future__ import annotations

import importlib.resources
import shutil
from pathlib import Path


SKILL_NAMES = [
    "obsidian-markdown",
    "json-canvas",
    "obsidian-bases",
    "obsidian-cli",
    "defuddle",
]


def install_skills(target_dir: Path) -> list[str]:
    """
    Copy all bundled skills into the target directory.

    Parameters
    ----------
    target_dir : Path
        Destination directory (typically ``.qwen/skills/``).

    Returns
    -------
    list[str]
        Names of installed skills.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    installed = []

    skills_pkg = "cortex.skills"

    for skill_name in SKILL_NAMES:
        src = target_dir / skill_name
        if src.exists():
            installed.append(f"{skill_name} (already exists)")
            continue

        try:
            src_ref = importlib.resources.files(skills_pkg).joinpath(skill_name)
            dest = target_dir / skill_name

            if src_ref.is_dir():
                # Copy entire skill directory
                _copy_tree(src_ref, dest)
            else:
                # Single file skill
                dest.write_text(src_ref.read_text(encoding="utf-8"), encoding="utf-8")

            installed.append(skill_name)
        except Exception:
            pass

    return installed


def _copy_tree(src_ref, dest: Path) -> None:
    """Recursively copy a directory tree from importlib resources to disk."""
    dest.mkdir(parents=True, exist_ok=True)

    try:
        entries = list(src_ref.iterdir())
    except Exception:
        return

    for entry_ref in entries:
        target = dest / entry_ref.name
        try:
            if entry_ref.is_dir():
                _copy_tree(entry_ref, target)
            else:
                target.write_text(entry_ref.read_text(encoding="utf-8"), encoding="utf-8")
        except Exception:
            pass
