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
    is_content_identical_to_bundle,
)

logger = logging.getLogger(__name__)


def _unique_backup(file_path: Path) -> Path:
    """``_backup_file`` con nombre unico (evita colisiones mismo-segundo
    entre injects consecutivos, que sobrescribirian el snapshot previo a
    Cortex que uninstall necesita para restaurar)."""
    backup = _backup_file(file_path)
    if not backup.exists():
        return backup
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")
    return backup.rename(backup.with_name(f"{file_path.name}.cortex_backup_{stamp}"))

#: Texto canonico que este adapter escribe en ``AGENTS.md``. Es la SSoT
#: tanto para install como para uninstall (deteccion de archivo 100% Cortex).
_CORTEX_AGENTS_MD = (
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
    + "\n"
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
        _unique_backup(agents_path)
        agents_path.write_text(_CORTEX_AGENTS_MD, encoding="utf-8")
        return [str(agents_path)]

    def inject_mcp(self, project_root: Path) -> list[str]:
        paths = self.get_config_paths()
        mcp_file = paths["mcp"]
        mcp_file.parent.mkdir(parents=True, exist_ok=True)

        _unique_backup(mcp_file)

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

    def uninstall(self, project_root: Path | None = None) -> list[str]:
        """Eliminar lo inyectado por Cortex en Windsurf.

        ``AGENTS.md`` fue SOBRESCRITO por ``inject_profiles`` (no mergeado),
        por lo que la restauracion es la via correcta:

        - Si existen backups ``AGENTS.md.cortex_backup_*`` -> se restaura el
          contenido del backup MAS VIEJO (el snapshot previo a cualquier
          modificacion de Cortex) y se eliminan los backups, que son
          artefactos 100% Cortex.
        - Si no hay backup y el contenido es identico al canonico Cortex ->
          el archivo fue creado integramente por Cortex y se borra.
        - Cualquier otro caso (mixto/desconocido) -> queda intacto y se
          reporta como ``skipped``.

        Ademas limpia ``mcpServers.cortex`` de
        ``~/.codeium/windsurf/mcp_config.json`` preservando otros servers.

        Sin ``project_root`` no se toca nada y se emite un warning explicito.
        """
        removed: list[str] = []

        if project_root is None:
            logger.warning(
                "[Cortex][Windsurf] uninstall() llamado sin project_root: "
                "no-op sobre AGENTS.md. Pasa el project root explicito."
            )
        else:
            root = Path(project_root).resolve()
            agents_path = root / "AGENTS.md"
            backups = sorted(agents_path.parent.glob("AGENTS.md.cortex_backup_*"))
            if backups:
                # El backup mas viejo es el estado previo a la primera
                # escritura de Cortex; los siguientes ya pueden contener
                # contenido Cortex regenerado.
                oldest = backups[0]
                agents_path.write_text(
                    oldest.read_text(encoding="utf-8"), encoding="utf-8"
                )
                removed.append(
                    f"{agents_path} (restored from {oldest.name})"
                )
                for backup in backups:
                    backup.unlink()
                    removed.append(str(backup))
            elif agents_path.exists():
                existing = agents_path.read_text(encoding="utf-8")
                if is_content_identical_to_bundle(existing, _CORTEX_AGENTS_MD):
                    agents_path.unlink()
                    removed.append(str(agents_path))
                else:
                    removed.append(
                        f"{agents_path} (skipped: mixed/unknown content)"
                    )

        # Limpiar entrada cortex del MCP config user-level.
        mcp_file = self.get_config_paths()["mcp"]
        if mcp_file.exists():
            with contextlib.suppress(Exception):
                data = json.loads(mcp_file.read_text(encoding="utf-8"))
                servers = data.get("mcpServers")
                if isinstance(servers, dict) and "cortex" in servers:
                    del servers["cortex"]
                    mcp_file.write_text(
                        json.dumps(data, indent=2), encoding="utf-8"
                    )
                    removed.append(f"{mcp_file} (cortex entry removed)")

        return removed
