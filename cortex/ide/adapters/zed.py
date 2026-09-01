from __future__ import annotations

import contextlib
import json
import logging
from pathlib import Path
from typing import Any

from cortex.ide.base import (
    IDEAdapter,
    _backup_file,
    _deep_merge_dict,
    _generate_autogen_header,
)

logger = logging.getLogger(__name__)

#: Claves canonicas que este adapter escribe en ``agents.json``.
_CORTEX_AGENT_KEYS: tuple[str, ...] = ("cortex-sync", "cortex-SDDwork")


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

    def uninstall(self, project_root: Path | None = None) -> list[str]:
        """Quitar los agents canonico de Cortex de ``~/.zed/agents.json``.

        Merge inverso: se eliminan SOLO las claves ``agents.cortex-sync`` y
        ``agents.cortex-SDDwork``; cualquier otro agent o clave del adopter
        queda intacto. ``project_root`` no aplica (config user-level) pero
        se acepta por contrato V2.
        """
        removed: list[str] = []
        agents_path = self.get_config_paths()["agents"]
        if not agents_path.exists():
            return removed

        try:
            data = json.loads(agents_path.read_text(encoding="utf-8"))
        except Exception:
            logger.warning(
                "[Cortex][Zed] %s no es JSON valido: skipped.", agents_path
            )
            return [f"{agents_path} (skipped: invalid JSON)"]

        agents = data.get("agents")
        changed = False
        if isinstance(agents, dict):
            for key in _CORTEX_AGENT_KEYS:
                if key in agents:
                    del agents[key]
                    changed = True
                    removed.append(f"{agents_path} (agent '{key}' removed)")

        if changed:
            agents_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return removed
