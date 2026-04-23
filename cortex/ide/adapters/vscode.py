from __future__ import annotations

import contextlib
import json
import platform
from pathlib import Path
from typing import Any

from cortex.ide.base import (
    IDEAdapter,
    _backup_file,
    _deep_merge_dict,
    _generate_autogen_header,
)


class VSCodeAdapter(IDEAdapter):
    @property
    def name(self) -> str:
        return "vscode"

    @property
    def display_name(self) -> str:
        return "VS Code"

    def get_config_paths(self) -> dict[str, Path]:
        # Detect OS and use appropriate VS Code settings path
        system = platform.system()
        if system == "Windows":
            # Windows: %APPDATA%\Code\User\settings.json
            import os
            appdata = os.environ.get("APPDATA", "")
            if appdata:
                settings_path = Path(appdata) / "Code" / "User" / "settings.json"
            else:
                # Fallback to default Windows path
                settings_path = Path.home() / "AppData" / "Roaming" / "Code" / "User" / "settings.json"
        elif system == "Darwin":  # macOS
            # macOS: ~/Library/Application Support/Code/User/settings.json
            settings_path = Path.home() / "Library" / "Application Support" / "Code" / "User" / "settings.json"
        else:  # Linux and others
            # Linux: ~/.config/Code/User/settings.json
            settings_path = Path.home() / ".config" / "Code" / "User" / "settings.json"

        return {
            "settings": settings_path,
        }

    def inject_profiles(self, project_root: Path, prompts: dict[str, str]) -> list[str]:
        github_dir = project_root / ".github"
        github_dir.mkdir(parents=True, exist_ok=True)

        header = _generate_autogen_header(
            sources=[".cortex/skills/cortex-sync.md", ".cortex/skills/cortex-SDDwork.md"],
            ide_name="vscode"
        )

        combined_prompt = f"{header}\n\n# Cortex Agent Profiles\n\n"
        for skill_name in ["cortex-sync", "cortex-SDDwork"]:
            if skill_name in prompts:
                combined_prompt += f"## {skill_name}\n{prompts[skill_name]}\n\n"

        instructions_path = github_dir / "copilot-instructions.md"
        _backup_file(instructions_path)
        instructions_path.write_text(combined_prompt, encoding="utf-8")

        return [str(instructions_path)]

    def inject_mcp(self, project_root: Path) -> list[str]:
        paths = self.get_config_paths()
        settings_path = paths["settings"]
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        _backup_file(settings_path)

        data: dict[str, Any] = {}
        if settings_path.exists():
            with contextlib.suppress(Exception):
                data = json.loads(settings_path.read_text(encoding="utf-8"))

        mcp_cmd = self._get_mcp_command(project_root)
        cortex_config = {
            "type": "stdio",
            "command": mcp_cmd["command"],
            "args": mcp_cmd["args"],
            "env": mcp_cmd["env"],
        }

        # Deep merge to preserve other MCP servers
        data.setdefault("github.copilot.mcp.servers", {})
        data["github.copilot.mcp.servers"] = _deep_merge_dict(
            data["github.copilot.mcp.servers"],
            {"cortex": cortex_config}
        )

        settings_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return [str(settings_path)]
