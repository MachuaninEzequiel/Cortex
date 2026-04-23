from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any

from cortex.ide.base import IDEAdapter, _backup_file, _deep_merge_dict, _append_to_markdown, _generate_autogen_header


class WindsurfAdapter(IDEAdapter):
    @property
    def name(self) -> str:
        return "windsurf"

    @property
    def display_name(self) -> str:
        return "Windsurf"

    def get_config_paths(self) -> dict[str, Path]:
        return {
            "mcp": Path.home() / ".codeium" / "windsurf" / "mcp_config.json",
        }

    def inject_profiles(self, project_root: Path, prompts: dict[str, str]) -> list[str]:
        rules_path = project_root / ".windsurfrules"

        header = _generate_autogen_header(
            sources=[".cortex/skills/cortex-sync.md", ".cortex/skills/cortex-SDDwork.md"],
            ide_name="windsurf"
        )

        combined_prompt = f"{header}\n\n# Cortex Agent Profiles\n\n"
        for skill_name in ["cortex-sync", "cortex-SDDwork"]:
            if skill_name in prompts:
                combined_prompt += f"## {skill_name}\n{prompts[skill_name]}\n\n"

        _backup_file(rules_path)
        rules_path.write_text(combined_prompt, encoding="utf-8")
        return [str(rules_path)]

    def inject_mcp(self, project_root: Path) -> list[str]:
        paths = self.get_config_paths()
        mcp_file = paths["mcp"]
        mcp_file.parent.mkdir(parents=True, exist_ok=True)

        _backup_file(mcp_file)

        data: dict[str, Any] = {"mcpServers": {}}
        if mcp_file.exists():
            with contextlib.suppress(Exception):
                data = json.loads(mcp_file.read_text(encoding="utf-8"))

        data.setdefault("mcpServers", {})

        mcp_cmd = self._get_mcp_command(project_root)
        cortex_config = {
            "command": mcp_cmd["command"],
            "args": mcp_cmd["args"],
            "env": mcp_cmd["env"],
        }

        # Deep merge to preserve other MCP servers
        data["mcpServers"] = _deep_merge_dict(data["mcpServers"], {"cortex": cortex_config})

        mcp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return [str(mcp_file)]
