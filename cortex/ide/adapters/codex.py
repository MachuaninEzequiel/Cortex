"""cortex.ide.adapters.codex — Codex CLI adapter.

Codex (the OpenAI ``codex`` CLI, https://github.com/openai/codex) is one of
the four IDE targets officially supported by Cortex. This adapter injects
Cortex profiles and the MCP server configuration into Codex's project-local
config directory (``.codex/``).

Layout written by this adapter, all under ``project_root``:

    .codex/
      AGENTS.md          ← top-level governance directive for the Codex agent
      mcp.json           ← MCP server registration (stdio, absolute --project-root)
      skills/
        cortex-sync.md
        cortex-sddwork.md
      agents/
        cortex-code-explorer.md
        cortex-code-implementer.md
        cortex-documenter.md
      autopilot.md       ← (managed by cortex.autopilot.adapters.codex)

Codex reads ``AGENTS.md`` at the project root by convention; Cortex writes
to ``.codex/AGENTS.md`` to avoid colliding with repos that already have a
top-level ``AGENTS.md`` (e.g. cortex-pi/).
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


def _render_codex_markdown(frontmatter: list[str], header: str, body: str) -> str:
    """Render a Codex agent/skill file with YAML frontmatter + HTML comment header."""
    fm_block = "\n".join(frontmatter)
    return f"---\n{fm_block}\n---\n\n<!--\n{header.strip()}\n-->\n\n{body.strip()}\n"


class CodexAdapter(IDEAdapter):
    """Adapter for the OpenAI Codex CLI.

    Codex uses a project-local ``.codex/`` directory plus an ``AGENTS.md``
    convention at the project root. This adapter follows the same shape
    as ``ClaudeCodeAdapter`` but namespaced under ``.codex/`` to avoid
    cross-IDE interference.
    """

    @property
    def name(self) -> str:
        return "codex"

    @property
    def display_name(self) -> str:
        return "Codex"

    def get_config_paths(self) -> dict[str, Path]:
        return {
            "agents_md": Path(".codex") / "AGENTS.md",
            "agents_dir": Path(".codex") / "agents",
            "skills_dir": Path(".codex") / "skills",
            "mcp": Path(".codex") / "mcp.json",
        }

    def inject_profiles(self, project_root: Path, prompts: dict[str, str]) -> list[str]:
        paths = self.get_config_paths()
        agents_md_path = project_root / paths["agents_md"]
        agents_dir = project_root / paths["agents_dir"]
        skills_dir = project_root / paths["skills_dir"]
        agents_md_path.parent.mkdir(parents=True, exist_ok=True)
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
            ide_name="codex",
        )

        files_written: list[str] = []

        _backup_file(agents_md_path)
        agents_md_path.write_text(
            "\n".join(
                [
                    "<!--",
                    header.strip(),
                    "-->",
                    "",
                    "# Cortex Workflow for Codex",
                    "",
                    "- Run `cortex-sync` before any implementation work to gather context and persist a spec.",
                    "- Run `cortex-sddwork` to implement the persisted spec using the Cortex routing rules.",
                    "- Delegate deep analysis to `cortex-code-explorer`, complex implementation to `cortex-code-implementer`, and final session persistence to `cortex-documenter`.",
                    "- Never call `cortex_create_spec` before `cortex_sync_ticket` — the MCP server rejects it with a governance violation.",
                    "",
                    "## Tripartita Refinada — verifiable contracts",
                    "",
                    "- The `cortex-documenter` MUST pass the **Verification Gate** before invoking `cortex_save_session`. Use `cortex_verify_session_claims` to cross-check claims against the actual git diff and label each memory with the resulting `confidence` (verified / asserted / contradicted).",
                    "- Every handoff between agents MUST be a YAML block validated by `cortex_validate_handoff` against the `AgentHandoff` schema. Codex has no native `Task` tool, so the handoff is the agent's last message — the next agent (or the user re-prompting in a new role) consumes that YAML as input.",
                    "- If a verification check fails or the work is partial, close the session with `status: handoff` (NOT `completed`) so the next agent knows there is open work to verify.",
                    "- If `CONTEXT.md` exists at the project root or under `.cortex/CONTEXT.md`, treat its terms as canonical and avoid forbidden synonyms. Suggest new domain terms via the handoff's `suggested_context_terms` field — only the documenter writes to `CONTEXT.md`.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        files_written.append(str(agents_md_path))

        skill_specs = {
            "cortex-sync": (
                "cortex-sync",
                "Create a Cortex spec before any implementation work.",
                strip_markdown_frontmatter(prompts.get("cortex-sync", "")),
                ".cortex/skills/cortex-sync.md",
            ),
            "cortex-sddwork": (
                "cortex-sddwork",
                "Implement a persisted Cortex spec using the Cortex workflow.",
                strip_markdown_frontmatter(prompts.get("cortex-SDDwork", "")),
                ".cortex/skills/cortex-SDDwork.md",
            ),
        }
        for directory_name, (skill_name, description, body, source) in skill_specs.items():
            skill_path = skills_dir / f"{directory_name}.md"
            _backup_file(skill_path)
            skill_path.write_text(
                _render_codex_markdown(
                    [
                        f"name: {skill_name}",
                        f"description: {description}",
                    ],
                    _generate_autogen_header(sources=[source], ide_name="codex"),
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
                _render_codex_markdown(
                    [
                        f"name: {agent_name}",
                        f"description: {description}",
                    ],
                    _generate_autogen_header(
                        sources=[f".cortex/subagents/{agent_name}.md"],
                        ide_name="codex",
                    ),
                    strip_markdown_frontmatter(get_subagent_prompt(project_root, agent_name)),
                ),
                encoding="utf-8",
            )
            files_written.append(str(agent_path))

        return files_written

    def inject_mcp(self, project_root: Path) -> list[str]:
        paths = self.get_config_paths()
        mcp_file = project_root / paths["mcp"]
        mcp_file.parent.mkdir(parents=True, exist_ok=True)

        _backup_file(mcp_file)

        data: dict[str, Any] = {"mcpServers": {}}
        if mcp_file.exists():
            with contextlib.suppress(Exception):
                data = json.loads(mcp_file.read_text(encoding="utf-8"))
        data.setdefault("mcpServers", {})

        # Absolute --project-root so Codex can locate the workspace
        # regardless of which directory it is launched from.
        cortex_config = {
            "type": "stdio",
            "command": "cortex",
            "args": ["mcp-server", "--stdio", "--project-root", str(project_root)],
            "env": {
                "PYTHONWARNINGS": "ignore",
            },
        }

        data["mcpServers"] = _deep_merge_dict(
            data["mcpServers"], {"cortex": cortex_config}
        )

        mcp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return [str(mcp_file)]

    def detect_installation(self) -> bool:
        """Detect whether the Codex CLI binary is available on PATH."""
        import shutil as _shutil

        return _shutil.which("codex") is not None

    def uninstall(self) -> list[str]:
        """Remove ``.codex/`` Cortex artifacts. Idempotent."""
        removed: list[str] = []
        cwd = Path.cwd()
        codex_dir = cwd / ".codex"
        if not codex_dir.exists():
            return removed

        # Only remove files Cortex owns; preserve user-authored content.
        for rel in (
            "AGENTS.md",
            "mcp.json",
            "agents/cortex-code-explorer.md",
            "agents/cortex-code-implementer.md",
            "agents/cortex-documenter.md",
            "skills/cortex-sync.md",
            "skills/cortex-sddwork.md",
        ):
            path = codex_dir / rel
            if path.exists():
                path.unlink()
                removed.append(str(path))

        # Drop empty Cortex-managed subdirectories.
        for subdir in ("agents", "skills"):
            d = codex_dir / subdir
            if d.exists() and not any(d.iterdir()):
                d.rmdir()
                removed.append(str(d))

        return removed
