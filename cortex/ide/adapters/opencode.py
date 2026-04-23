from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any

from cortex.ide.base import (
    IDEAdapter,
    _backup_file,
    _deep_merge_dict,
    _generate_autogen_header,
)


class OpenCodeAdapter(IDEAdapter):
    @property
    def name(self) -> str:
        return "opencode"

    @property
    def display_name(self) -> str:
        return "OpenCode"

    def get_config_paths(self) -> dict[str, Path]:
        config_dir = Path.home() / ".config" / "opencode"
        return {
            "main": config_dir / "opencode.json",
            "skills_dir": config_dir / "skills",
            "subagents_dir": config_dir / "subagents",
        }

    def needs_wsl_shielding(self) -> bool:
        return True

    def inject_profiles(self, project_root: Path, prompts: dict[str, str]) -> list[str]:
        paths = self.get_config_paths()
        config_file = paths["main"]
        skills_dir = paths["skills_dir"]
        subagents_dir = paths["subagents_dir"]

        skills_dir.mkdir(parents=True, exist_ok=True)
        subagents_dir.mkdir(parents=True, exist_ok=True)
        files_written = []

        header = _generate_autogen_header(
            sources=[".cortex/skills/cortex-sync.md", ".cortex/skills/cortex-SDDwork.md"],
            ide_name="opencode"
        )

        # Write core skills with header
        for skill_name, content in prompts.items():
            skill_file = skills_dir / f"{skill_name}.md"
            _backup_file(skill_file)
            skill_file.write_text(f"{header}\n\n{content}", encoding="utf-8")
            files_written.append(str(skill_file))

        # Copy subagents with header
        cortex_subagents_dir = project_root / ".cortex" / "subagents"
        if cortex_subagents_dir.exists():
            for subagent_file in cortex_subagents_dir.glob("*.md"):
                dest = subagents_dir / subagent_file.name
                _backup_file(dest)
                subagent_header = _generate_autogen_header(
                    sources=[f".cortex/subagents/{subagent_file.name}"],
                    ide_name="opencode"
                )
                dest.write_text(f"{subagent_header}\n\n{subagent_file.read_text(encoding='utf-8')}", encoding="utf-8")
                files_written.append(str(dest))

        # Read existing config
        data: dict[str, Any] = {}
        if config_file.exists():
            with contextlib.suppress(Exception):
                data = json.loads(config_file.read_text(encoding="utf-8"))

        _backup_file(config_file)

        data.setdefault("agent", {})

        # OpenCode specific profile map
        cortex_profiles = {
            "cortex-sync": {
                "mode": "primary",
                "description": "PRE-FLIGHT: Context gathering and spec preparation.",
                "prompt": f"{{file:{skills_dir / 'cortex-sync.md'}}}",
                "tools": {
                    "read": True, "write": False, "edit": False, "bash": False,
                    "cortex_context": True, "cortex_search": True,
                    "cortex_search_vector": True, "cortex_sync_ticket": True,
                    "cortex_create_spec": True, "cortex_sync_vault": True,
                },
            },
            "cortex-SDDwork": {
                "mode": "primary",
                "description": "ORCHESTRATOR: Fast Track direct edits or Deep Track delegation.",
                "prompt": f"{{file:{skills_dir / 'cortex-SDDwork.md'}}}",
                "tools": {
                    "read": True, "write": True, "edit": True, "bash": False,
                    "cortex_context": True, "cortex_search": True,
                    "cortex_search_vector": True, "cortex_save_session": True,
                    "cortex_sync_vault": True, "Task": True,
                },
            },
        }

        # Deep merge to preserve other agent profiles
        data["agent"] = _deep_merge_dict(data["agent"], cortex_profiles)

        config_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        files_written.append(str(config_file))
        return files_written

    def inject_mcp(self, project_root: Path) -> list[str]:
        paths = self.get_config_paths()
        config_file = paths["main"]

        _backup_file(config_file)

        data: dict[str, Any] = {}
        if config_file.exists():
            with contextlib.suppress(Exception):
                data = json.loads(config_file.read_text(encoding="utf-8"))

        data.setdefault("mcp", {})
        cortex_config = {
            "type": "local",
            **self._get_mcp_command(project_root),
            "enabled": True,
        }

        # Deep merge to preserve other MCP servers
        data["mcp"] = _deep_merge_dict(data["mcp"], {"cortex": cortex_config})

        config_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return [str(config_file)]
