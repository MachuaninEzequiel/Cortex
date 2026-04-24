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


def _render_claude_markdown(frontmatter: list[str], header: str, body: str) -> str:
    frontmatter_block = "\n".join(frontmatter)
    return f"---\n{frontmatter_block}\n---\n\n<!--\n{header.strip()}\n-->\n\n{body.strip()}\n"


class ClaudeCodeAdapter(IDEAdapter):
    @property
    def name(self) -> str:
        return "claude_code"

    @property
    def display_name(self) -> str:
        return "Claude Code"

    def get_config_paths(self) -> dict[str, Path]:
        return {
            "claude_md": Path("CLAUDE.md"),
            "agents_dir": Path(".claude") / "agents",
            "skills_dir": Path(".claude") / "skills",
            "settings": Path(".claude") / "settings.json",
            "mcp": Path(".mcp.json"),
        }

    def inject_profiles(self, project_root: Path, prompts: dict[str, str]) -> list[str]:
        paths = self.get_config_paths()
        claude_md_path = project_root / paths["claude_md"]
        agents_dir = project_root / paths["agents_dir"]
        skills_dir = project_root / paths["skills_dir"]
        agents_dir.mkdir(parents=True, exist_ok=True)
        skills_dir.mkdir(parents=True, exist_ok=True)

        header = _generate_autogen_header(
            sources=[
                ".cortex/skills/cortex-sync.md",
                ".cortex/skills/cortex-SDDwork.md",
                ".cortex/subagents/cortex-code-explorer.md",
                ".cortex/subagents/cortex-code-implementer.md",
                ".cortex/subagents/cortex-documenter.md",
            ],
            ide_name="claude_code",
        )

        files_written: list[str] = []

        _backup_file(claude_md_path)
        claude_md_path.write_text(
            "\n".join(
                [
                    "<!--",
                    header.strip(),
                    "-->",
                    "",
                    "# Cortex Workflow",
                    "",
                    "- Use `/cortex-sync` before implementation to gather context and persist a spec.",
                    "- Use `/cortex-sddwork` to implement the persisted spec with Cortex routing rules.",
                    "- Delegate deep analysis to `cortex-code-explorer`, complex implementation to `cortex-code-implementer`, and final session persistence to `cortex-documenter`.",
                    "- Never call `cortex_create_spec` before `cortex_sync_ticket`.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        files_written.append(str(claude_md_path))

        skill_specs = {
            "cortex-sync": (
                "cortex-sync",
                "Create a Cortex spec before any implementation work.",
                strip_markdown_frontmatter(prompts.get("cortex-sync", "")),
            ),
            "cortex-sddwork": (
                "cortex-sddwork",
                "Implement a persisted Cortex spec using the Cortex workflow.",
                strip_markdown_frontmatter(prompts.get("cortex-SDDwork", "")),
            ),
        }
        for directory_name, (skill_name, description, body) in skill_specs.items():
            skill_dir = skills_dir / directory_name
            skill_dir.mkdir(parents=True, exist_ok=True)
            skill_path = skill_dir / "SKILL.md"
            _backup_file(skill_path)
            skill_path.write_text(
                _render_claude_markdown(
                    [
                        f"name: {skill_name}",
                        f"description: {description}",
                    ],
                    _generate_autogen_header(
                        sources=[f".cortex/skills/{'cortex-SDDwork.md' if directory_name == 'cortex-sddwork' else 'cortex-sync.md'}"],
                        ide_name="claude_code",
                    ),
                    body,
                ),
                encoding="utf-8",
            )
            files_written.append(str(skill_path))

        agent_specs = {
            "cortex-code-explorer": "Read-only architecture analysis for complex changes.",
            "cortex-code-implementer": "Deep-track implementation specialist for complex changes.",
            "cortex-documenter": "Persist sessions and create Cortex documentation artifacts.",
        }
        for agent_name, description in agent_specs.items():
            agent_path = agents_dir / f"{agent_name}.md"
            _backup_file(agent_path)
            agent_path.write_text(
                _render_claude_markdown(
                    [
                        f"name: {agent_name}",
                        f"description: {description}",
                    ],
                    _generate_autogen_header(
                        sources=[f".cortex/subagents/{agent_name}.md"],
                        ide_name="claude_code",
                    ),
                    strip_markdown_frontmatter(get_subagent_prompt(project_root, agent_name)),
                ),
                encoding="utf-8",
            )
            files_written.append(str(agent_path))

        return files_written

    def inject_mcp(self, project_root: Path) -> list[str]:
        paths = self.get_config_paths()
        settings_path = project_root / paths["settings"]
        mcp_file = project_root / paths["mcp"]
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        mcp_file.parent.mkdir(parents=True, exist_ok=True)

        _backup_file(settings_path)
        _backup_file(mcp_file)

        settings_data: dict[str, Any] = {}
        if settings_path.exists():
            with contextlib.suppress(Exception):
                settings_data = json.loads(settings_path.read_text(encoding="utf-8"))

        enabled_servers = settings_data.get("enabledMcpjsonServers", [])
        if not isinstance(enabled_servers, list):
            enabled_servers = []
        if "cortex" not in enabled_servers:
            enabled_servers.append("cortex")
        settings_data["enabledMcpjsonServers"] = enabled_servers

        data: dict[str, Any] = {"mcpServers": {}}
        if mcp_file.exists():
            with contextlib.suppress(Exception):
                data = json.loads(mcp_file.read_text(encoding="utf-8"))

        data.setdefault("mcpServers", {})

        cortex_config = {
            "type": "stdio",
            "command": "cortex",
            "args": ["mcp-server", "--stdio", "--project-root", "."],
            "env": {
                "PYTHONWARNINGS": "ignore",
            },
        }

        data["mcpServers"] = _deep_merge_dict(data["mcpServers"], {"cortex": cortex_config})

        settings_path.write_text(json.dumps(settings_data, indent=2), encoding="utf-8")
        mcp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return [str(settings_path), str(mcp_file)]
