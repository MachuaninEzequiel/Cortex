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

#: Claves canonicas que este adapter escribe bajo ``prompts``.
_CORTEX_PROMPT_KEYS: tuple[str, ...] = ("cortex-sync", "cortex-SDDwork")


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

    def uninstall(self, project_root: Path | None = None) -> list[str]:
        """Quitar lo inyectado por Cortex de ``~/.config/hermes/config.json``.

        Merge inverso: se eliminan SOLO ``prompts.{cortex-sync,cortex-SDDwork}``
        y ``mcp.cortex``; cualquier otra prompt/server/clave del adopter queda
        intacta. ``project_root`` no aplica (config user-level) pero se acepta
        por contrato V2.
        """
        removed: list[str] = []
        config_path = self.get_config_paths()["config"]
        if not config_path.exists():
            return removed

        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            logger.warning(
                "[Cortex][Hermes] %s no es JSON valido: skipped.", config_path
            )
            return [f"{config_path} (skipped: invalid JSON)"]

        changed = False

        prompts = data.get("prompts")
        if isinstance(prompts, dict):
            for key in _CORTEX_PROMPT_KEYS:
                if key in prompts:
                    del prompts[key]
                    changed = True
                    removed.append(f"{config_path} (prompt '{key}' removed)")

        mcp = data.get("mcp")
        if isinstance(mcp, dict) and "cortex" in mcp:
            del mcp["cortex"]
            changed = True
            removed.append(f"{config_path} (cortex entry removed)")

        if changed:
            config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return removed
