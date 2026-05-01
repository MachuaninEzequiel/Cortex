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
from cortex.ide.prompts import build_cursor_prompts


class CursorAdapter(IDEAdapter):
    @property
    def name(self) -> str:
        return "cursor"

    @property
    def display_name(self) -> str:
        return "Cursor"

    def get_config_paths(self) -> dict[str, Path]:
        base_dir = Path.home() / ".cursor"
        return {
            "mcp": base_dir / "mcp.json",
            "agents_dir": base_dir / "agents",
        }

    def inject_profiles(self, project_root: Path, prompts: dict[str, str] | None = None) -> list[str]:
        """Inject Cortex agent profiles for Cursor.

        Cursor uses a hybrid architecture with 3 subagents:
        - cortex-sync: Pre-flight analysis
        - cortex-SDDwork-cursor: Hybrid orchestrator (explorer + implementer)
        - cortex-documenter: Documentation specialist

        Args:
            project_root: Path to the Cortex project root.
            prompts: Optional dict of prompts. If None, uses Cursor-specific prompts.

        Returns:
            List of files written/modified.
        """
        paths = self.get_config_paths()
        agents_dir = paths["agents_dir"]
        agents_dir.mkdir(parents=True, exist_ok=True)

        # Use Cursor-specific prompts if not provided
        if prompts is None:
            prompts = build_cursor_prompts(project_root)

        header = _generate_autogen_header(
            sources=[
                ".cortex/skills/cortex-sync.md",
                ".cortex/skills/cortex-SDDwork-cursor.md",
                ".cortex/subagents/cortex-documenter.md"
            ],
            ide_name="cursor"
        )

        files_written = []
        for skill_name, content in prompts.items():
            skill_path = agents_dir / f"{skill_name}.md"
            _backup_file(skill_path)
            skill_path.write_text(f"{header}\n\n{content}", encoding="utf-8")
            files_written.append(str(skill_path))

        return files_written

    def inject_mcp(self, project_root: Path) -> list[str]:
        """Inject MCP server configuration for Cursor.

        Uses --project-root argument to ensure Cortex finds config.yaml
        regardless of Cursor's working directory.
        """
        paths = self.get_config_paths()
        mcp_file = paths["mcp"]
        mcp_file.parent.mkdir(parents=True, exist_ok=True)

        _backup_file(mcp_file)

        data: dict[str, Any] = {"mcpServers": {}}
        if mcp_file.exists():
            with contextlib.suppress(Exception):
                data = json.loads(mcp_file.read_text(encoding="utf-8"))

        data.setdefault("mcpServers", {})

        # Cursor-specific MCP config with --project-root
        cortex_config = {
            "command": "cortex",
            "args": [
                "mcp-server",
                "--stdio",
                "--project-root",
                str(project_root)
            ],
            "env": {
                "PYTHONWARNINGS": "ignore"
            }
        }

        # Deep merge to preserve other MCP servers
        data["mcpServers"] = _deep_merge_dict(data["mcpServers"], {"cortex": cortex_config})

        mcp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return [str(mcp_file)]
