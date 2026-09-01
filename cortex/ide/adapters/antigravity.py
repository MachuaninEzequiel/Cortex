from __future__ import annotations

import contextlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from cortex.ide.base import (
    IDEAdapter,
    _backup_file,
    _deep_merge_dict,
    _generate_autogen_header,
)

logger = logging.getLogger(__name__)


def _unique_backup(file_path: Path) -> Path:
    """``_backup_file`` con nombre unico.

    El timestamp de ``_backup_file`` tiene granularidad de segundos: dos
    injects en el mismo segundo (p.ej. profiles + MCP seguidos) colisionan
    y el segundo backup SOBRESCRIBE al primero, destruyendo el snapshot
    previo a Cortex que uninstall necesita para restaurar.
    """
    backup = _backup_file(file_path)
    if not backup.exists():
        return backup
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")
    return backup.rename(backup.with_name(f"{file_path.name}.cortex_backup_{stamp}"))


class AntigravityAdapter(IDEAdapter):
    @property
    def name(self) -> str:
        return "antigravity"

    @property
    def display_name(self) -> str:
        return "Antigravity (Gemini Code Assist)"

    def get_config_paths(self) -> dict[str, Path]:
        return {
            "settings": Path.home() / ".gemini" / "settings.json",
        }

    def inject_profiles(self, project_root: Path, prompts: dict[str, str]) -> list[str]:
        paths = self.get_config_paths()
        settings_path = paths["settings"]
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        _unique_backup(settings_path)

        data: dict[str, Any] = {}
        if settings_path.exists():
            with contextlib.suppress(Exception):
                data = json.loads(settings_path.read_text(encoding="utf-8"))

        data.setdefault("system_instructions", "")

        header = _generate_autogen_header(
            sources=[".cortex/skills/cortex-sync.md", ".cortex/skills/cortex-SDDwork.md"],
            ide_name="antigravity"
        )

        combined_prompt = f"{header}\n\nYou are working in a Cortex project. Please follow these profiles:\n\n"
        for skill_name in ["cortex-sync", "cortex-SDDwork"]:
            if skill_name in prompts:
                combined_prompt += f"## {skill_name}\n{prompts[skill_name]}\n\n"

        # Replace instructions (not append, since this is JSON)
        data["system_instructions"] = combined_prompt

        settings_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return [str(settings_path)]

    def inject_mcp(self, project_root: Path) -> list[str]:
        paths = self.get_config_paths()
        settings_path = paths["settings"]
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        _unique_backup(settings_path)

        data: dict[str, Any] = {}
        if settings_path.exists():
            with contextlib.suppress(Exception):
                data = json.loads(settings_path.read_text(encoding="utf-8"))

        data.setdefault("mcp_servers", {})

        mcp_cmd = self._get_mcp_command(project_root)
        cortex_config = {
            "command": mcp_cmd["command"],
            "args": mcp_cmd["args"],
            "env": mcp_cmd["env"],
        }

        # Deep merge to preserve other MCP servers
        data["mcp_servers"] = _deep_merge_dict(data["mcp_servers"], {"cortex": cortex_config})

        settings_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return [str(settings_path)]

    def uninstall(self, project_root: Path | None = None) -> list[str]:
        """Revertir lo inyectado por Cortex en ``~/.gemini/settings.json``.

        - Si existen backups ``settings.json.cortex_backup_*`` -> se restaura
          el valor previo de ``system_instructions`` desde el backup MAS
          VIEJO (snapshot previo a la primera escritura de Cortex) y se
          eliminan los backups (artefactos 100% Cortex).
        - Sin backup, si las instrucciones actuales son generadas por Cortex
          -> se resetean a vacio (el default que usa el propio inject).
        - Se limpia ``mcp_servers.cortex`` preservando el resto.

        ``project_root`` no aplica (config user-level) pero se acepta por
        contrato V2.
        """
        removed: list[str] = []
        settings_path = self.get_config_paths()["settings"]
        if not settings_path.exists():
            return removed

        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception:
            logger.warning(
                "[Cortex][Antigravity] %s no es JSON valido: skipped.",
                settings_path,
            )
            return [f"{settings_path} (skipped: invalid JSON)"]

        backups = sorted(settings_path.parent.glob("settings.json.cortex_backup_*"))
        restored = False
        # El backup util es el MAS VIEJO cuyo system_instructions NO sea
        # generado por Cortex (los backups posteriores ya pueden contener
        # instrucciones Cortex regeneradas por inject_mcp).
        for candidate in backups:
            backup_data: dict[str, Any] | None = None
            with contextlib.suppress(Exception):
                backup_data = json.loads(candidate.read_text(encoding="utf-8"))
            if backup_data is None:
                continue
            instructions = backup_data.get("system_instructions")
            if isinstance(instructions, str) and "AUTOGENERATED BY CORTEX" in instructions:
                continue
            data["system_instructions"] = instructions
            restored = True
            removed.append(
                f"{settings_path} (system_instructions restored from {candidate.name})"
            )
            break
        cleared = False
        if not restored:
            instructions = data.get("system_instructions")
            if isinstance(instructions, str) and "AUTOGENERATED BY CORTEX" in instructions:
                data["system_instructions"] = ""
                cleared = True
                removed.append(f"{settings_path} (Cortex system_instructions cleared)")

        for backup in backups:
            backup.unlink()
            removed.append(str(backup))

        servers = data.get("mcp_servers")
        changed = False
        if isinstance(servers, dict) and "cortex" in servers:
            del servers["cortex"]
            changed = True
            removed.append(f"{settings_path} (cortex entry removed)")

        if changed or restored or cleared:
            settings_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return removed
