from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any

from cortex.ide.base import IDEAdapter, _backup_file, _deep_merge_dict, _generate_autogen_header


class AntigravityAdapter(IDEAdapter):
    @property
    def name(self) -> str:
        return "antigravity"

    @property
    def display_name(self) -> str:
        return "Antigravity (Gemini Code Assist)"

    def get_config_paths(self) -> dict[str, Path]:
        return {
            "settings": Path.home() / ".gemini" / "settings.json",
        }

    def inject_profiles(self, project_root: Path, prompts: dict[str, str]) -> list[str]:
        paths = self.get_config_paths()
        settings_path = paths["settings"]
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        _backup_file(settings_path)

        data: dict[str, Any] = {}
        if settings_path.exists():
            with contextlib.suppress(Exception):
                data = json.loads(settings_path.read_text(encoding="utf-8"))

        data.setdefault("system_instructions", "")

        header = _generate_autogen_header(
            sources=[".cortex/skills/cortex-sync.md", ".cortex/skills/cortex-SDDwork.md"],
            ide_name="antigravity"
        )

        combined_prompt = f"{header}\n\nYou are working in a Cortex project. Please follow these profiles:\n\n"
        for skill_name in ["cortex-sync", "cortex-SDDwork"]:
            if skill_name in prompts:
                combined_prompt += f"## {skill_name}\n{prompts[skill_name]}\n\n"

        # Replace instructions (not append, since this is JSON)
        data["system_instructions"] = combined_prompt

        settings_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return [str(settings_path)]

    def inject_mcp(self, project_root: Path) -> list[str]:
        paths = self.get_config_paths()
        settings_path = paths["settings"]
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        _backup_file(settings_path)

        data: dict[str, Any] = {}
        if settings_path.exists():
            with contextlib.suppress(Exception):
                data = json.loads(settings_path.read_text(encoding="utf-8"))

        data.setdefault("mcp_servers", {})

        mcp_cmd = self._get_mcp_command(project_root)
        cortex_config = {
            "command": mcp_cmd["command"],
            "args": mcp_cmd["args"],
            "env": mcp_cmd["env"],
        }

        # Deep merge to preserve other MCP servers
        data["mcp_servers"] = _deep_merge_dict(data["mcp_servers"], {"cortex": cortex_config})

        settings_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return [str(settings_path)]
