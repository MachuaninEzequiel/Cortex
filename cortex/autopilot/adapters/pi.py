"""cortex.autopilot.adapters.pi — Pi Coding Agent adapter for Autopilot.

Pi is project-local and uses ``.pi/settings.json``, ``.pi/extensions/*.ts``,
and ``.pi/skills/*``.  This adapter installs a Pi extension and skill that
connect Pi session events to the Autopilot CLI.
"""
from __future__ import annotations

import json
from pathlib import Path

from cortex.autopilot.adapters.base import (
    _backup_path,
    format_session_start_output,
)
from cortex.autopilot.models import AutopilotSessionState


def _pi_dir(project_root: Path) -> Path:
    return project_root / ".pi"


def _settings_path(project_root: Path) -> Path:
    return _pi_dir(project_root) / "settings.json"


def _extension_dest(project_root: Path) -> Path:
    return _pi_dir(project_root) / "extensions" / "cortex-autopilot.ts"


def _skill_dest(project_root: Path) -> Path:
    return (
        _pi_dir(project_root)
        / "skills"
        / "using-cortex-autopilot"
        / "SKILL.md"
    )


def _extension_template() -> Path:
    return (
        Path(__file__).resolve().parent.parent
        / "pi"
        / "extensions"
        / "cortex-autopilot.ts"
    )


def _skill_template() -> Path:
    return (
        Path(__file__).resolve().parent.parent
        / "pi"
        / "skills"
        / "using-cortex-autopilot"
        / "SKILL.md"
    )


def _load_settings(path: Path) -> dict:
    """Load *path* as JSON.  Return a minimal default if missing."""
    if not path.exists():
        return {"defaultExtensions": [], "skills": []}
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def _merge_settings(settings: dict) -> dict:
    """Add Autopilot entries to *settings* without duplicating."""
    settings = dict(settings)

    for key in ("defaultExtensions", "skills"):
        if key not in settings:
            settings[key] = []
        if not isinstance(settings[key], list):
            raise ValueError(
                f"Expected {key!r} to be a list, got {type(settings[key]).__name__}"
            )

    ext_entry = "extensions/cortex-autopilot.ts"
    if ext_entry not in settings["defaultExtensions"]:
        settings["defaultExtensions"].append(ext_entry)

    skill_entry = ".pi/skills/using-cortex-autopilot/SKILL.md"
    if skill_entry not in settings["skills"]:
        settings["skills"].append(skill_entry)

    return settings


def _remove_settings_entries(settings: dict) -> dict:
    """Remove Autopilot entries from *settings*."""
    settings = dict(settings)
    ext_entry = "extensions/cortex-autopilot.ts"
    skill_entry = ".pi/skills/using-cortex-autopilot/SKILL.md"

    for key, entry in (
        ("defaultExtensions", ext_entry),
        ("skills", skill_entry),
    ):
        if key in settings and isinstance(settings[key], list):
            settings[key] = [e for e in settings[key] if e != entry]

    return settings


class PiAutopilotAdapter:
    name = "pi"
    supported_events = {"session_start", "session_finish"}

    def install(self, project_root: Path) -> list[Path]:
        """Install Pi Autopilot extension and skill into *project_root*."""
        root = Path(project_root)
        created: list[Path] = []

        # Ensure directories exist
        _extension_dest(root).parent.mkdir(parents=True, exist_ok=True)
        _skill_dest(root).parent.mkdir(parents=True, exist_ok=True)

        # Copy extension template
        ext_src = _extension_template()
        ext_dst = _extension_dest(root)
        if ext_src.exists():
            ext_dst.write_text(ext_src.read_text(encoding="utf-8"), encoding="utf-8")
            created.append(ext_dst)

        # Copy skill template
        skill_src = _skill_template()
        skill_dst = _skill_dest(root)
        if skill_src.exists():
            skill_dst.write_text(skill_src.read_text(encoding="utf-8"), encoding="utf-8")
            created.append(skill_dst)

        # Merge settings
        settings_path = _settings_path(root)
        settings = _load_settings(settings_path)
        merged = _merge_settings(settings)

        if settings_path.exists():
            backup = _backup_path(settings_path)
            settings_path.rename(backup)
        settings_path.write_text(
            json.dumps(merged, indent=2) + "\n", encoding="utf-8"
        )
        created.append(settings_path)

        return created

    def uninstall(self, project_root: Path) -> list[Path]:
        """Remove Pi Autopilot extension and skill from *project_root*."""
        root = Path(project_root)
        removed: list[Path] = []

        ext_dst = _extension_dest(root)
        if ext_dst.exists():
            ext_dst.unlink()
            removed.append(ext_dst)

        skill_dst = _skill_dest(root)
        skill_parent = skill_dst.parent
        if skill_dst.exists():
            skill_dst.unlink()
            removed.append(skill_dst)
        if skill_parent.exists() and not any(skill_parent.iterdir()):
            skill_parent.rmdir()

        settings_path = _settings_path(root)
        if settings_path.exists():
            settings = _load_settings(settings_path)
            cleaned = _remove_settings_entries(settings)
            settings_path.write_text(
                json.dumps(cleaned, indent=2) + "\n", encoding="utf-8"
            )
            removed.append(settings_path)

        return removed

    def emit_session_start(self, state: AutopilotSessionState, bootstrap: str) -> str:
        return format_session_start_output(state, bootstrap, "pi")
