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
from cortex.ide.canonical_tools import translate_list
from cortex.ide.prompts import (
    get_subagent_prompt,
    split_markdown_frontmatter,
    strip_markdown_frontmatter,
)


def _render_claude_markdown(frontmatter: list[str], header: str, body: str) -> str:
    frontmatter_block = "\n".join(frontmatter)
    return f"---\n{frontmatter_block}\n---\n\n<!--\n{header.strip()}\n-->\n\n{body.strip()}\n"


def _parse_canonical_tools(frontmatter_text: str | None) -> list[str]:
    """Parse el campo ``tools:`` del frontmatter de un prompt canonico.

    Los renders en ``cortex_workspace.py`` usan formato comma-separated:

        tools: read_file, write_file, cortex_save_session, cortex_ping

    Devuelve la lista de tool names canonicos. Lista vacia si no hay
    frontmatter o no hay campo tools.
    """
    if not frontmatter_text:
        return []
    for line in frontmatter_text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("tools:"):
            value = stripped.split(":", 1)[1].strip()
            return [t.strip() for t in value.split(",") if t.strip()]
    return []


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
                ".cortex/skills/cortex-documenter.md",
                ".cortex/subagents/cortex-code-explorer.md",
                ".cortex/subagents/cortex-code-implementer.md",
                ".cortex/subagents/cortex-code-designer.md",
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
                    "# Cortex Workflow — Triadic Anchors (Phase 09.A+ / May 2026)",
                    "",
                    "Cortex se ejecuta con TRES skills invocables con `/`. El medio es",
                    "pluggable; los anchors de inicio y cierre son **obligatorios**.",
                    "",
                    "1. **`/cortex-sync`** (anchor inicio, obligatorio) — carga contexto",
                    "   histórico via ONNX/RRF, emite propuesta interactiva, persiste la",
                    "   spec en el vault, abre la Session.",
                    "2. **Middle (pluggable)** — uno de los siguientes:",
                    "   - **`/cortex-SDDwork`** (Managed): Fast Track edits directos o Deep",
                    "     Track con delegación a los subagents canónicos.",
                    "   - Subagents directos via Task tool: `cortex-code-explorer`,",
                    "     `cortex-code-designer`, `cortex-code-implementer` (Deep Track).",
                    "   - **BYO**: trabajás manualmente o con cualquier otro agente. Cortex",
                    "     reconstruye desde el diff al cierre.",
                    "3. **`/cortex-documenter`** (anchor cierre, obligatorio) — invoca",
                    "   `cortex_documenter_briefing`, decide qué doc types persistir",
                    "   (session / handoff / adr / decision / runbook / etc.), escribe la",
                    "   nota a mano con criterio editorial, llama `cortex_self_review_note`,",
                    "   persiste vía `cortex_write_doc` y cierra con `cortex_close_session`.",
                    "",
                    "## Hard rules",
                    "",
                    "- NUNCA llames `cortex_create_spec` antes de `cortex_sync_ticket` (el MCP",
                    "  server rechaza con violación de gobernanza).",
                    "- NUNCA omitas `/cortex-documenter` al final — sin el cierre con criterio",
                    "  editorial, la sesión queda con documentación de baja señal y la memoria",
                    "  organizacional se erosiona.",
                    "- El status `handoff` es un outcome de primera clase. Si los verification",
                    "  hooks fallan o quedan archivos unimplemented, cerrar como `handoff`",
                    "  (NO `closed`) para que el próximo `/cortex-sync` lo priorice.",
                    "- Si `CONTEXT.md` existe, los términos del dominio son canónicos.",
                    "  `/cortex-documenter` puede agregar nuevos términos vía `cortex_write_doc`",
                    "  con `doc_type=glossary`.",
                    "",
                    "## Subagents canónicos (Task tool)",
                    "",
                    "Disponibles para que `/cortex-SDDwork` delegue trabajo en Deep Track:",
                    "",
                    "- `cortex-code-explorer` — análisis de arquitectura read-only.",
                    "- `cortex-code-designer` — produce design doc antes de implementar.",
                    "- `cortex-code-implementer` — implementa siguiendo el design doc.",
                    "- `cortex-documenter` (DEPRECATED) — solo para compatibilidad con flujos",
                    "  antiguos; el flujo canónico de cierre es `/cortex-documenter`.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        files_written.append(str(claude_md_path))

        # Phase 09.A+ / May 2026: the three triadic anchors are installed
        # as slash-invocable skills. ``cortex-documenter`` joins ``cortex-sync``
        # and ``cortex-sddwork`` as the third skill. The legacy subagent
        # under ``.claude/agents/cortex-documenter.md`` is kept for backward
        # compat (see ``agent_specs`` below) but flagged as deprecated.
        skill_specs = {
            "cortex-sync": (
                "cortex-sync",
                "Create a Cortex spec before any implementation work.",
                ".cortex/skills/cortex-sync.md",
                strip_markdown_frontmatter(prompts.get("cortex-sync", "")),
            ),
            "cortex-sddwork": (
                "cortex-sddwork",
                "Implement a persisted Cortex spec using the Cortex workflow.",
                ".cortex/skills/cortex-SDDwork.md",
                strip_markdown_frontmatter(prompts.get("cortex-SDDwork", "")),
            ),
            "cortex-documenter": (
                "cortex-documenter",
                "Close a Cortex Session with editorial criterion (anchor de cierre).",
                ".cortex/skills/cortex-documenter.md",
                strip_markdown_frontmatter(prompts.get("cortex-documenter", "")),
            ),
        }
        for directory_name, (skill_name, description, source_path, body) in skill_specs.items():
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
                        sources=[source_path],
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
            # Phase 09.A+ / May 2026: kept for backward compat with the
            # legacy Reconstruction flow. New code closes Sessions via the
            # /cortex-documenter SLASH SKILL above; the subagent path is
            # only used by single-agent IDEs (Codex, Pi) that don't have
            # slash dispatch. The subagent's source file already carries
            # the DEPRECATED banner.
            "cortex-documenter": "DEPRECATED — use /cortex-documenter skill instead. Persist sessions via the legacy Reconstruction flow.",
        }
        for agent_name, description in agent_specs.items():
            agent_path = agents_dir / f"{agent_name}.md"
            _backup_file(agent_path)

            # Leer el prompt canonico y separar frontmatter del body. El
            # frontmatter del canonico declara los tools en vocabulario
            # canonico de Cortex; los traducimos al formato de Claude Code
            # (PascalCase + ``mcp__cortex__<tool>``) via ``translate_list``.
            canonical_md = get_subagent_prompt(project_root, agent_name)
            canonical_frontmatter, canonical_body = split_markdown_frontmatter(canonical_md)
            canonical_tools = _parse_canonical_tools(canonical_frontmatter)
            # ``_parse_canonical_tools`` returns ``list[str]`` (we cannot
            # narrow the literal at parse time). ``translate_list`` raises
            # ``UnknownCanonicalToolError`` for unknown tools, so the
            # runtime contract is enforced; the type-ignore here only
            # silences the static literal-vs-str mismatch.
            translated_tools = translate_list(canonical_tools, "claude_code")  # type: ignore[arg-type]

            frontmatter_lines = [
                f"name: {agent_name}",
                f"description: {description}",
            ]
            # Solo inyectar ``tools:`` si el canonico declara tools. Sin la
            # linea, Claude Code hereda TODAS las tools del padre — eso
            # viola la restriccion declarada por el prompt canonico.
            if translated_tools:
                frontmatter_lines.append(f"tools: {', '.join(translated_tools)}")

            agent_path.write_text(
                _render_claude_markdown(
                    frontmatter_lines,
                    _generate_autogen_header(
                        sources=[f".cortex/subagents/{agent_name}.md"],
                        ide_name="claude_code",
                    ),
                    canonical_body,
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

        # Use an absolute project_root so Claude Code can locate the
        # Cortex workspace regardless of which directory the IDE process
        # is launched from. Relative "." breaks when the IDE is opened
        # via spotlight, drag-and-drop, or a shortcut.
        cortex_config = {
            "type": "stdio",
            "command": "cortex",
            "args": ["mcp-server", "--stdio", "--project-root", str(project_root)],
            "env": {
                "PYTHONWARNINGS": "ignore",
            },
        }

        data["mcpServers"] = _deep_merge_dict(data["mcpServers"], {"cortex": cortex_config})

        settings_path.write_text(json.dumps(settings_data, indent=2), encoding="utf-8")
        mcp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return [str(settings_path), str(mcp_file)]
