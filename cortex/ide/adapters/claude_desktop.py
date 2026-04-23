from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any

from cortex.ide.base import IDEAdapter, _backup_file, _deep_merge_dict


class ClaudeDesktopAdapter(IDEAdapter):
    @property
    def name(self) -> str:
        return "claude_desktop"

    @property
    def display_name(self) -> str:
        return "Claude Desktop"

    def get_config_paths(self) -> dict[str, Path]:
        # Support macOS and Windows/Linux variations
        paths = [
            Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
            Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
        ]
        
        # Pick the one that exists, or default to .config for Linux/WSL
        target = paths[1]
        for p in paths:
            if p.exists() or p.parent.exists():
                target = p
                break
                
        return {"mcp": target}

    def needs_wsl_shielding(self) -> bool:
        return True

    def inject_profiles(self, project_root: Path, prompts: dict[str, str]) -> list[str]:
        # Claude Desktop only uses MCP, it doesn't have local agent profiles
        return []

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
            "enabled": True,
        }

        # Deep merge to preserve other MCP servers
        data["mcpServers"] = _deep_merge_dict(data["mcpServers"], {"cortex": cortex_config})

        mcp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return [str(mcp_file)]
