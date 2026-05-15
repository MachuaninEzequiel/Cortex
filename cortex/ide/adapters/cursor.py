"""cortex.ide.adapters.cursor — Cursor IDE adapter.

Rediseno completo en Fase 4 del plan multi-IDE & MCP hardening (2026-05-15)
basado en validacion contra documentacion oficial de Cursor 2.4+:

    https://cursor.com/docs/subagents

Decision 3 firmada del creador: usar los 3 subagents canonicos reales
(``cortex-code-explorer``, ``cortex-code-implementer``, ``cortex-documenter``)
en ``.cursor/agents/``. Eliminado el adapter hibrido pre-2.4 con
``cortex-SDDwork-cursor.md`` (variante por IDE en la SSoT que violaba el
principio rector #1).

Layout escrito por este adapter:

    .cursor/
      agents/
        cortex-code-explorer.md       ← subagent canonico
        cortex-code-implementer.md    ← subagent canonico
        cortex-documenter.md          ← subagent canonico
      mcp.json                        ← MCP server registration

Cursor frontmatter campos soportados (segun docs oficiales 2026):

- ``name``: identificador (default: derivado del filename)
- ``description``: cuando usar el subagent
- ``model``: ``inherit`` por default
- ``readonly``: bool, default false
- ``is_background``: bool, default false

NO se declara ``tools:`` en frontmatter — Cursor subagents heredan TODAS
las tools del padre. Esto es el comportamiento documentado oficialmente.
"""
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
from cortex.ide.prompts import get_subagent_prompt, strip_markdown_frontmatter

# Subagents canonicos de Cortex que se inyectan en Cursor. Coincide con la
# lista en claude_code y otros adapters validados — el mismo flujo
# tripartito en todos los IDEs que soportan subagents.
_CORTEX_SUBAGENTS: dict[str, dict[str, Any]] = {
    "cortex-code-explorer": {
        "description": "Read-only architecture analysis for complex changes.",
        "readonly": True,
    },
    "cortex-code-implementer": {
        "description": "Deep-track implementation specialist for complex changes.",
        "readonly": False,
    },
    "cortex-documenter": {
        "description": "Persist sessions and create Cortex documentation artifacts.",
        "readonly": False,
    },
}


def _render_cursor_subagent(
    name: str,
    description: str,
    readonly: bool,
    autogen_header: str,
    body: str,
) -> str:
    """Render un subagent file en formato Cursor 2.4+.

    Cursor frontmatter: name, description, model, readonly, is_background.
    NO incluir ``tools:`` — Cursor subagents heredan del padre.
    """
    frontmatter = [
        f"name: {name}",
        f"description: {description}",
        "model: inherit",
        f"readonly: {'true' if readonly else 'false'}",
    ]
    fm_block = "\n".join(frontmatter)
    return f"---\n{fm_block}\n---\n\n<!--\n{autogen_header.strip()}\n-->\n\n{body.strip()}\n"


class CursorAdapter(IDEAdapter):
    @property
    def name(self) -> str:
        return "cursor"

    @property
    def display_name(self) -> str:
        return "Cursor"

    def get_config_paths(self) -> dict[str, Path]:
        # Project-level por default (Cursor 2.4+ docs: ``.cursor/agents/``).
        # User-level (``~/.cursor/agents/``) sigue siendo soportado pero
        # project-level se prefiere para que los subagents convivan con
        # el repo y se versionen.
        base_dir = Path.home() / ".cursor"
        return {
            "mcp": base_dir / "mcp.json",
            "user_agents_dir": base_dir / "agents",
            # project-level paths se resuelven dinamicamente con project_root.
            "project_agents_dir_relative": Path(".cursor") / "agents",
        }

    def inject_profiles(self, project_root: Path, prompts: dict[str, str] | None = None) -> list[str]:
        """Inyecta los 3 subagents canonicos en ``.cursor/agents/`` (project-level).

        ``prompts`` se acepta por uniformidad con el contrato base pero NO
        se usa: los subagents se leen desde ``.cortex/subagents/*.md`` (la
        SSoT de Cortex), respetando el principio rector #1.
        """
        del prompts  # leemos directo de la SSoT canonica via get_subagent_prompt

        agents_dir = project_root / Path(".cursor") / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        files_written: list[str] = []
        for agent_name, spec in _CORTEX_SUBAGENTS.items():
            agent_path = agents_dir / f"{agent_name}.md"
            _backup_file(agent_path)

            autogen_header = _generate_autogen_header(
                sources=[f".cortex/subagents/{agent_name}.md"],
                ide_name="cursor",
            )
            canonical_body = strip_markdown_frontmatter(
                get_subagent_prompt(project_root, agent_name)
            )

            agent_path.write_text(
                _render_cursor_subagent(
                    name=agent_name,
                    description=spec["description"],
                    readonly=spec["readonly"],
                    autogen_header=autogen_header,
                    body=canonical_body,
                ),
                encoding="utf-8",
            )
            files_written.append(str(agent_path))

        return files_written

    def inject_mcp(self, project_root: Path) -> list[str]:
        """Inject MCP server configuration for Cursor.

        Cursor MCP config va en ``~/.cursor/mcp.json`` (user-level por
        defecto, segun docs oficiales). Usa --project-root absoluto para
        que Cortex localice la workspace independientemente del cwd
        de Cursor al arrancar.
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

        cortex_config = {
            "command": "cortex",
            "args": [
                "mcp-server",
                "--stdio",
                "--project-root",
                str(project_root),
            ],
            "env": {
                "PYTHONWARNINGS": "ignore",
            },
        }

        # Deep merge to preserve other MCP servers
        data["mcpServers"] = _deep_merge_dict(data["mcpServers"], {"cortex": cortex_config})

        mcp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return [str(mcp_file)]

    def uninstall(self) -> list[str]:
        """Eliminar los subagents inyectados en ``.cursor/agents/`` y
        limpiar la entrada Cortex de ``~/.cursor/mcp.json``.

        Conservador: solo elimina archivos que el adapter Cortex genera,
        no toca el directorio entero ni otros agents/MCP servers que el
        adopter pueda tener.
        """
        removed: list[str] = []
        cwd = Path.cwd()

        # 1. Project-level subagents
        project_agents_dir = cwd / ".cursor" / "agents"
        for agent_name in _CORTEX_SUBAGENTS:
            agent_path = project_agents_dir / f"{agent_name}.md"
            if agent_path.exists():
                agent_path.unlink()
                removed.append(str(agent_path))
        # Drop empty .cursor/agents/ directory
        if project_agents_dir.exists() and not any(project_agents_dir.iterdir()):
            project_agents_dir.rmdir()
            removed.append(str(project_agents_dir))

        # 2. Limpiar entrada Cortex de MCP config (user-level)
        mcp_file = self.get_config_paths()["mcp"]
        if mcp_file.exists():
            with contextlib.suppress(Exception):
                data = json.loads(mcp_file.read_text(encoding="utf-8"))
                if "mcpServers" in data and "cortex" in data["mcpServers"]:
                    del data["mcpServers"]["cortex"]
                    mcp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
                    removed.append(f"{mcp_file} (cortex entry removed)")

        return removed
