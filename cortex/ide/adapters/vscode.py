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


def _render_vscode_agent(frontmatter: list[str], header: str, body: str) -> str:
    frontmatter_block = "\n".join(frontmatter)
    return f"---\n{frontmatter_block}\n---\n\n<!--\n{header.strip()}\n-->\n\n{body.strip()}\n"


def _render_claude_agent(name: str, description: str, header: str, body: str) -> str:
    return (
        f"---\n"
        f"name: {name}\n"
        f"description: {description}\n"
        f"---\n\n"
        f"<!--\n{header.strip()}\n-->\n\n"
        f"{body.strip()}\n"
    )


class VSCodeAdapter(IDEAdapter):
    @property
    def name(self) -> str:
        return "vscode"

    @property
    def display_name(self) -> str:
        return "VS Code"

    def get_config_paths(self) -> dict[str, Path]:
        return {
            "mcp": Path(".vscode") / "mcp.json",
            "agents_dir": Path(".github") / "agents",
            "claude_agents_dir": Path(".claude") / "agents",
        }

    def inject_profiles(self, project_root: Path, prompts: dict[str, str]) -> list[str]:
        paths = self.get_config_paths()
        agents_dir = project_root / paths["agents_dir"]
        claude_agents_dir = project_root / paths["claude_agents_dir"]
        agents_dir.mkdir(parents=True, exist_ok=True)
        claude_agents_dir.mkdir(parents=True, exist_ok=True)

        sync_body = strip_markdown_frontmatter(prompts.get("cortex-sync", ""))
        work_body = strip_markdown_frontmatter(prompts.get("cortex-SDDwork", ""))

        top_level_header = _generate_autogen_header(
            sources=[".cortex/skills/cortex-sync.md", ".cortex/skills/cortex-SDDwork.md"],
            ide_name="vscode",
        )
        subagent_sources = {
            "cortex-code-explorer": (
                "Read-only architecture analysis for complex changes.",
                ".cortex/subagents/cortex-code-explorer.md",
            ),
            "cortex-code-implementer": (
                "Deep-track implementation specialist for complex changes.",
                ".cortex/subagents/cortex-code-implementer.md",
            ),
            "cortex-documenter": (
                "Session documentation and vault persistence specialist.",
                ".cortex/subagents/cortex-documenter.md",
            ),
        }

        files_written: list[str] = []

        sync_path = agents_dir / "cortex-sync.agent.md"
        _backup_file(sync_path)
        sync_path.write_text(
            _render_vscode_agent(
                [
                    "name: cortex-sync",
                    "description: Create Cortex specs before implementation.",
                    "tools: ['search/codebase', 'search/usages', 'cortex/*']",
                    "handoffs:",
                    "  - label: Continue with cortex-SDDwork",
                    "    agent: cortex-SDDwork",
                    "    prompt: Continue from the persisted Cortex spec and execute the implementation workflow.",
                    "    send: false",
                ],
                top_level_header,
                sync_body,
            ),
            encoding="utf-8",
        )
        files_written.append(str(sync_path))

        work_path = agents_dir / "cortex-SDDwork.agent.md"
        _backup_file(work_path)
        work_path.write_text(
            _render_vscode_agent(
                [
                    "name: cortex-SDDwork",
                    "description: Implement Cortex specs with fast-track or deep-track routing.",
                    "tools: ['agent', 'edit', 'search/codebase', 'search/usages', 'cortex/*']",
                    "agents: ['cortex-code-explorer', 'cortex-code-implementer', 'cortex-documenter']",
                ],
                top_level_header,
                work_body,
            ),
            encoding="utf-8",
        )
        files_written.append(str(work_path))

        for agent_name, (description, source) in subagent_sources.items():
            agent_header = _generate_autogen_header(sources=[source], ide_name="vscode")
            agent_path = claude_agents_dir / f"{agent_name}.md"
            _backup_file(agent_path)
            agent_path.write_text(
                _render_claude_agent(
                    agent_name,
                    description,
                    agent_header,
                    strip_markdown_frontmatter(get_subagent_prompt(project_root, agent_name)),
                ),
                encoding="utf-8",
            )
            files_written.append(str(agent_path))

        return files_written

    def inject_mcp(self, project_root: Path) -> list[str]:
        mcp_path = project_root / self.get_config_paths()["mcp"]
        mcp_path.parent.mkdir(parents=True, exist_ok=True)
        _backup_file(mcp_path)

        data: dict[str, Any] = {}
        if mcp_path.exists():
            with contextlib.suppress(Exception):
                data = json.loads(mcp_path.read_text(encoding="utf-8"))

        cortex_config = {
            "type": "stdio",
            "command": "cortex",
            "args": ["mcp-server", "--stdio", "--project-root", "${workspaceFolder}"],
            "env": {"PYTHONWARNINGS": "ignore"},
        }

        data.setdefault("servers", {})
        data["servers"] = _deep_merge_dict(data["servers"], {"cortex": cortex_config})

        mcp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return [str(mcp_path)]
