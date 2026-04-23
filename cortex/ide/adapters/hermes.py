from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any

from cortex.ide.base import IDEAdapter, _backup_file, _deep_merge_dict, _generate_autogen_header


class HermesAdapter(IDEAdapter):
    @property
    def name(self) -> str:
        return "hermes"

    @property
    def display_name(self) -> str:
        return "Hermes"

    def get_config_paths(self) -> dict[str, Path]:
        return {
            "config": Path.home() / ".config" / "hermes" / "config.json",
        }

    def inject_profiles(self, project_root: Path, prompts: dict[str, str]) -> list[str]:
        paths = self.get_config_paths()
        config_path = paths["config"]
        config_path.parent.mkdir(parents=True, exist_ok=True)

        _backup_file(config_path)

        data: dict[str, Any] = {}
        if config_path.exists():
            with contextlib.suppress(Exception):
                data = json.loads(config_path.read_text(encoding="utf-8"))

        data.setdefault("prompts", {})

        header = _generate_autogen_header(
            sources=[".cortex/skills/cortex-sync.md", ".cortex/skills/cortex-SDDwork.md"],
            ide_name="hermes"
        )

        cortex_prompts = {}
        for skill_name in ["cortex-sync", "cortex-SDDwork"]:
            if skill_name in prompts:
                cortex_prompts[skill_name] = f"{header}\n\n{prompts[skill_name]}"

        # Deep merge to preserve other prompts
        data["prompts"] = _deep_merge_dict(data["prompts"], cortex_prompts)

        config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return [str(config_path)]

    def inject_mcp(self, project_root: Path) -> list[str]:
        paths = self.get_config_paths()
        config_path = paths["config"]
        config_path.parent.mkdir(parents=True, exist_ok=True)

        _backup_file(config_path)

        data: dict[str, Any] = {}
        if config_path.exists():
            with contextlib.suppress(Exception):
                data = json.loads(config_path.read_text(encoding="utf-8"))

        data.setdefault("mcp", {})

        mcp_cmd = self._get_mcp_command(project_root)
        cortex_config = {
            "command": mcp_cmd["command"],
            "args": mcp_cmd["args"],
            "env": mcp_cmd["env"],
        }

        # Deep merge to preserve other MCP servers
        data["mcp"] = _deep_merge_dict(data["mcp"], {"cortex": cortex_config})

        config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return [str(config_path)]
