from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any

from cortex.ide.base import IDEAdapter, _backup_file, _deep_merge_dict, _generate_autogen_header


class ZedAdapter(IDEAdapter):
    @property
    def name(self) -> str:
        return "zed"

    @property
    def display_name(self) -> str:
        return "Zed"

    def get_config_paths(self) -> dict[str, Path]:
        return {
            "agents": Path.home() / ".zed" / "agents.json",
        }

    def inject_profiles(self, project_root: Path, prompts: dict[str, str]) -> list[str]:
        paths = self.get_config_paths()
        agents_path = paths["agents"]
        agents_path.parent.mkdir(parents=True, exist_ok=True)

        _backup_file(agents_path)

        header = _generate_autogen_header(
            sources=[".cortex/skills/cortex-sync.md", ".cortex/skills/cortex-SDDwork.md"],
            ide_name="zed"
        )

        # In Zed, we write the prompts into agents.json directly
        data: dict[str, Any] = {}
        if agents_path.exists():
            with contextlib.suppress(Exception):
                data = json.loads(agents_path.read_text(encoding="utf-8"))

        data.setdefault("agents", {})

        cortex_agents = {}
        if "cortex-sync" in prompts:
            cortex_agents["cortex-sync"] = {
                "name": "Cortex Sync",
                "description": "Pre-flight analysis with context injection",
                "system_prompt": f"{header}\n\n{prompts['cortex-sync']}",
            }

        if "cortex-SDDwork" in prompts:
            cortex_agents["cortex-SDDwork"] = {
                "name": "Cortex SDDwork",
                "description": "Implementation orchestrator",
                "system_prompt": f"{header}\n\n{prompts['cortex-SDDwork']}",
            }

        # Deep merge to preserve other agents
        data["agents"] = _deep_merge_dict(data["agents"], cortex_agents)

        agents_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return [str(agents_path)]

    def inject_mcp(self, project_root: Path) -> list[str]:
        # Zed supports MCP via its extensions or settings, but typically requires manual config.
        # We'll leave a stub or log message if it needs special handling.
        return []
