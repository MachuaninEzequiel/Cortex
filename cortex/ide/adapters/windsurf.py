from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any

from cortex.ide.base import (
    IDEAdapter,
    _backup_file,
    _deep_merge_dict,
)


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
        agents_path = project_root / "AGENTS.md"
        agents_path.parent.mkdir(parents=True, exist_ok=True)
        _backup_file(agents_path)
        agents_path.write_text(
            "\n".join(
                [
                    "# Cortex Workflow",
                    "",
                    "Follow this Cortex workflow for every task in this repository:",
                    "",
                    "1. Start with pre-flight analysis. Call `cortex_sync_ticket` with the user's request before creating any spec with `cortex_create_spec`.",
                    "2. Inspect only the relevant files, then persist the implementation spec.",
                    "3. Implement directly for simple changes. For complex changes, do deeper analysis first and then implement with minimal, focused edits.",
                    "4. Finish every completed implementation by calling `cortex_save_session` with the changed files, technical decisions, validation results, and next steps.",
                    "",
                    "Additional Cortex rules:",
                    "",
                    "- Never call `cortex_create_spec` before `cortex_sync_ticket`.",
                    "- Do not over-engineer simple tasks.",
                    "- Keep the final session summary concise but complete enough for future retrieval.",
                    "- If a Cortex MCP tool fails, stop and report the blocker instead of inventing context.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return [str(agents_path)]

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

        cortex_config = {
            "command": "cortex",
            "args": ["mcp-server", "--stdio", "--project-root", str(project_root)],
            "env": {"PYTHONWARNINGS": "ignore"},
        }

        data["mcpServers"] = _deep_merge_dict(data["mcpServers"], {"cortex": cortex_config})

        mcp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return [str(mcp_file)]
