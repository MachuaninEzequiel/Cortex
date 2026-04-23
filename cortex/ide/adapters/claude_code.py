from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any

from cortex.ide.base import IDEAdapter, _backup_file, _deep_merge_dict, _append_to_markdown, _generate_autogen_header


class ClaudeCodeAdapter(IDEAdapter):
    @property
    def name(self) -> str:
        return "claude_code"

    @property
    def display_name(self) -> str:
        return "Claude Code"

    def get_config_paths(self) -> dict[str, Path]:
        return {
            "profiles_dir": Path.home() / ".claude",
            "mcp": Path.home() / ".config" / "claude" / "mcp.json",
        }

    def inject_profiles(self, project_root: Path, prompts: dict[str, str]) -> list[str]:
        paths = self.get_config_paths()
        profiles_dir = paths["profiles_dir"]
        profiles_dir.mkdir(parents=True, exist_ok=True)

        header = _generate_autogen_header(
            sources=[".cortex/skills/cortex-sync.md", ".cortex/skills/cortex-SDDwork.md"],
            ide_name="claude_code"
        )

        files_written = []
        for skill_name, content in prompts.items():
            skill_path = profiles_dir / f"{skill_name}.md"
            _backup_file(skill_path)
            skill_path.write_text(f"{header}\n\n{content}", encoding="utf-8")
            files_written.append(str(skill_path))

        return files_written

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
            "type": "stdio",
            "command": mcp_cmd["command"],
            "args": mcp_cmd["args"],
            "env": mcp_cmd["env"],
        }

        # Deep merge to preserve other MCP servers
        data["mcpServers"] = _deep_merge_dict(data["mcpServers"], {"cortex": cortex_config})

        mcp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return [str(mcp_file)]
