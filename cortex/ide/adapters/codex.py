"""cortex.ide.adapters.codex — Codex CLI adapter.

Codex (the OpenAI ``codex`` CLI, https://github.com/openai/codex) is one of
the four IDE targets officially supported by Cortex.

Rediseno completo en Fase 4 del plan multi-IDE & MCP hardening (2026-05-15)
basado en validacion contra documentacion oficial:

- https://developers.openai.com/codex/guides/agents-md
- https://developers.openai.com/codex/mcp

Diferencias clave vs version anterior:

1. **AGENTS.md va al project root**, NO ``.codex/AGENTS.md``. Codex lee
   ``AGENTS.md`` en project root (con merge layered desde ``~/.codex/AGENTS.md``
   global y directorios padre). El path anterior ``.codex/AGENTS.md`` era
   ignorado por Codex.

2. **Codex NO soporta subagents personalizados.** Decision 2 del creador
   firmada en `MATRIZ-NATIVA-IDES.md`: el agente unico ejecuta las 3 fases
   tripartitas (explorer + implementer + documenter) **secuencialmente**
   dentro de la misma sesion, guiado por instrucciones explicitas en
   ``AGENTS.md``.

3. **MCP config en TOML**, no JSON. Sintaxis: ``[mcp_servers.<name>]`` con
   seccion separada ``[mcp_servers.<name>.env]`` para variables de entorno.

4. ``.codex/agents/`` y ``.codex/skills/`` no se generan (Codex los ignora).

Layout escrito por este adapter:

    AGENTS.md             ← project root, instrucciones del flujo tripartito
                            secuencial
    .codex/
      config.toml         ← MCP server registration en TOML
"""
from __future__ import annotations

import re
from pathlib import Path

from cortex.ide.base import (
    IDEAdapter,
    _backup_file,
    _generate_autogen_header,
)

# Marcadores para localizar la seccion Cortex dentro de AGENTS.md preexistentes.
# El AGENTS.md del adopter puede ya tener contenido propio; Cortex appendea su
# bloque entre estos marcadores y reemplaza solo lo que esta entre ellos.
_CORTEX_AGENTS_MD_MARKER_OPEN = "<!-- BEGIN CORTEX SECTION (auto-generated, do not edit) -->"
_CORTEX_AGENTS_MD_MARKER_CLOSE = "<!-- END CORTEX SECTION -->"

# Marcador para el bloque MCP en config.toml. Permite reemplazar limpiamente
# el bloque Cortex sin tocar otros servers MCP que el adopter pueda tener.
_CORTEX_TOML_MARKER_OPEN = "# BEGIN CORTEX MCP (auto-generated, do not edit)"
_CORTEX_TOML_MARKER_CLOSE = "# END CORTEX MCP"


def _build_cortex_agents_section(autogen_header: str) -> str:
    """Devuelve el bloque Cortex que se inyecta en AGENTS.md del project root.

    Codex no soporta subagents personalizados — el agente unico ejecuta las
    3 fases tripartitas secuencialmente. El AGENTS.md instruye explicitamente
    el orden y los gates de cada fase.
    """
    return f"""{_CORTEX_AGENTS_MD_MARKER_OPEN}
<!--
{autogen_header.strip()}
-->

# Cortex Workflow for Codex

This project uses Cortex governance. Codex executes the Cortex tripartite
flow as a **single-agent sequence** because Codex has no native `Task`
tool for parallel subagent delegation — see
`docs/architecture/canonical-tools.md`.

## Pre-flight check (mandatory)

Before any operation, call `cortex_ping`. If the response is not
`status: "ok"`, abort the operation with a clear message to the user:

> The Cortex MCP server is unavailable (status: <status>; last_error:
> <error>). Restart the IDE or run `cortex doctor` to diagnose.

NEVER fall back to manual markdown writing. NEVER degrade Cortex features
when the MCP is down.

## Sequential tripartite flow

For each non-trivial task, execute the 3 phases **in this exact order**
within the same session:

### Phase 1 — Explorer (read-only analysis)

- Use `cortex_search` and `cortex_context` to find relevant files.
- Read ONLY what the spec mentions or what is essential.
- DO NOT modify any code in this phase.
- At the end of this phase, summarize verified facts and unverified
  assumptions in your message before moving to Phase 2.

### Phase 2 — Implementer (code changes)

- Read the explorer summary above (still in your context).
- Modify code following the existing repo conventions.
- Run tests if available; report failures explicitly.
- Use `cortex_validate_handoff` to validate the YAML `AgentHandoff`
  structure before declaring the phase complete. Status `handoff` is a
  first-class outcome — use it when work is partial, NOT `completed`.

### Phase 3 — Documenter (Verification Gate + persistence)

The Verification Gate is mandatory before persisting any session note:

- Use `cortex_verify_session_claims` to cross-check every claim against
  the actual git diff. If a verification fails, close the session with
  `status: handoff` (NOT `completed`).
- Persist the session note via `cortex_save_session` with the verified
  state, decisions, and next steps.

## Hard rules

- NEVER call `cortex_create_spec` before `cortex_sync_ticket`. The MCP
  server rejects it with a governance violation.
- ALWAYS pass through the Verification Gate (Phase 3) before closing the
  session.
- If `CONTEXT.md` exists at project root or under `.cortex/CONTEXT.md`,
  treat its terms as canonical. Suggest new domain terms via the
  handoff's `suggested_context_terms` field.

{_CORTEX_AGENTS_MD_MARKER_CLOSE}
"""


def _replace_or_append_cortex_section(existing: str, cortex_block: str) -> str:
    """Reemplaza el bloque Cortex en ``existing`` o lo appendea al final.

    Si ``existing`` ya contiene los marcadores Cortex, reemplaza todo lo que
    esta entre ellos. Si no, appendea el bloque al final (con un separador).
    Esto permite a Cortex coexistir con AGENTS.md del adopter sin pisarle
    instrucciones propias.
    """
    pattern = re.compile(
        re.escape(_CORTEX_AGENTS_MD_MARKER_OPEN)
        + r".*?"
        + re.escape(_CORTEX_AGENTS_MD_MARKER_CLOSE),
        re.DOTALL,
    )
    if pattern.search(existing):
        return pattern.sub(cortex_block.strip(), existing)
    # Append: separator only if existing has content and doesn't end with newline
    sep = "" if not existing else ("\n" if existing.endswith("\n") else "\n\n")
    return existing + sep + cortex_block


def _build_cortex_toml_block(project_root: Path) -> str:
    """Devuelve el bloque TOML de configuracion del MCP server Cortex.

    Sintaxis exacta segun docs oficiales:

        [mcp_servers.cortex]
        command = "cortex"
        args = ["mcp-server", "--stdio", "--project-root", "<path>"]
        enabled = true

        [mcp_servers.cortex.env]
        PYTHONWARNINGS = "ignore"

    El path se inyecta como TOML string (escapado para Windows backslashes).
    """
    project_str = str(project_root).replace("\\", "\\\\")
    return f"""{_CORTEX_TOML_MARKER_OPEN}
[mcp_servers.cortex]
command = "cortex"
args = ["mcp-server", "--stdio", "--project-root", "{project_str}"]
enabled = true

[mcp_servers.cortex.env]
PYTHONWARNINGS = "ignore"
{_CORTEX_TOML_MARKER_CLOSE}
"""


def _replace_or_append_cortex_toml_block(existing: str, cortex_toml: str) -> str:
    """Reemplaza el bloque Cortex en ``existing`` config.toml o lo appendea."""
    pattern = re.compile(
        re.escape(_CORTEX_TOML_MARKER_OPEN)
        + r".*?"
        + re.escape(_CORTEX_TOML_MARKER_CLOSE),
        re.DOTALL,
    )
    if pattern.search(existing):
        return pattern.sub(cortex_toml.strip(), existing)
    sep = "" if not existing else ("\n" if existing.endswith("\n") else "\n\n")
    return existing + sep + cortex_toml


class CodexAdapter(IDEAdapter):
    """Adapter for the OpenAI Codex CLI."""

    @property
    def name(self) -> str:
        return "codex"

    @property
    def display_name(self) -> str:
        return "Codex"

    def get_config_paths(self) -> dict[str, Path]:
        return {
            "agents_md": Path("AGENTS.md"),  # project root, NOT inside .codex/
            "config_toml": Path(".codex") / "config.toml",
        }

    def inject_profiles(self, project_root: Path, prompts: dict[str, str]) -> list[str]:
        """Inyectar AGENTS.md en project root con instrucciones del flujo Cortex.

        ``prompts`` se acepta por uniformidad con la base IDEAdapter pero
        no se usa: Codex no soporta subagents ni skills personalizados,
        toda la guidance va inline en AGENTS.md.
        """
        del prompts  # no aplicable a Codex

        paths = self.get_config_paths()
        agents_md_path = project_root / paths["agents_md"]
        agents_md_path.parent.mkdir(parents=True, exist_ok=True)

        autogen_header = _generate_autogen_header(
            sources=[
                ".cortex/skills/cortex-sync.md",
                ".cortex/skills/cortex-SDDwork.md",
                ".cortex/subagents/cortex-code-explorer.md",
                ".cortex/subagents/cortex-code-implementer.md",
                ".cortex/subagents/cortex-documenter.md",
            ],
            ide_name="codex",
        )
        cortex_block = _build_cortex_agents_section(autogen_header)

        existing = ""
        if agents_md_path.exists():
            _backup_file(agents_md_path)
            existing = agents_md_path.read_text(encoding="utf-8")

        new_content = _replace_or_append_cortex_section(existing, cortex_block)
        agents_md_path.write_text(new_content, encoding="utf-8")
        return [str(agents_md_path)]

    def inject_mcp(self, project_root: Path) -> list[str]:
        """Inyectar el MCP server Cortex en ``.codex/config.toml`` (TOML, no JSON).

        Sintaxis validada contra https://developers.openai.com/codex/mcp.
        """
        paths = self.get_config_paths()
        config_path = project_root / paths["config_toml"]
        config_path.parent.mkdir(parents=True, exist_ok=True)

        cortex_toml = _build_cortex_toml_block(project_root)

        existing = ""
        if config_path.exists():
            _backup_file(config_path)
            existing = config_path.read_text(encoding="utf-8")

        new_content = _replace_or_append_cortex_toml_block(existing, cortex_toml)
        config_path.write_text(new_content, encoding="utf-8")
        return [str(config_path)]

    def detect_installation(self) -> bool:
        """Detect whether the Codex CLI binary is available on PATH."""
        import shutil as _shutil

        return _shutil.which("codex") is not None

    def uninstall(self) -> list[str]:
        """Remove Cortex sections from AGENTS.md and config.toml. Idempotent.

        Conservador: solo elimina los BLOQUES marcados como Cortex (entre
        marcadores ``BEGIN CORTEX SECTION`` / ``END CORTEX SECTION`` en
        AGENTS.md, y ``BEGIN CORTEX MCP`` / ``END CORTEX MCP`` en
        config.toml). NO elimina archivos completos para no destruir
        contenido del adopter.

        Tambien limpia archivos legacy (``.codex/AGENTS.md``, ``.codex/agents/``,
        ``.codex/skills/``, ``.codex/mcp.json``) que el adapter pre-Fase 4
        creaba pero Codex nunca leia.
        """
        removed: list[str] = []
        cwd = Path.cwd()

        # 1. Limpiar bloque Cortex de AGENTS.md en project root
        agents_md = cwd / "AGENTS.md"
        if agents_md.exists():
            existing = agents_md.read_text(encoding="utf-8")
            pattern = re.compile(
                re.escape(_CORTEX_AGENTS_MD_MARKER_OPEN)
                + r".*?"
                + re.escape(_CORTEX_AGENTS_MD_MARKER_CLOSE)
                + r"\n?",
                re.DOTALL,
            )
            cleaned = pattern.sub("", existing).rstrip() + "\n"
            if cleaned != existing:
                if cleaned.strip():
                    agents_md.write_text(cleaned, encoding="utf-8")
                    removed.append(f"{agents_md} (Cortex section removed)")
                else:
                    agents_md.unlink()
                    removed.append(str(agents_md))

        # 2. Limpiar bloque Cortex de .codex/config.toml
        config_toml = cwd / ".codex" / "config.toml"
        if config_toml.exists():
            existing = config_toml.read_text(encoding="utf-8")
            pattern = re.compile(
                re.escape(_CORTEX_TOML_MARKER_OPEN)
                + r".*?"
                + re.escape(_CORTEX_TOML_MARKER_CLOSE)
                + r"\n?",
                re.DOTALL,
            )
            cleaned = pattern.sub("", existing).rstrip() + "\n"
            if cleaned != existing:
                if cleaned.strip():
                    config_toml.write_text(cleaned, encoding="utf-8")
                    removed.append(f"{config_toml} (Cortex MCP block removed)")
                else:
                    config_toml.unlink()
                    removed.append(str(config_toml))

        # 3. Limpieza de artefactos legacy del adapter pre-Fase 4 (Codex
        # nunca los leyo, pero pueden quedar de instalaciones viejas).
        legacy_paths = [
            cwd / ".codex" / "AGENTS.md",
            cwd / ".codex" / "mcp.json",
            cwd / ".codex" / "agents" / "cortex-code-explorer.md",
            cwd / ".codex" / "agents" / "cortex-code-implementer.md",
            cwd / ".codex" / "agents" / "cortex-documenter.md",
            cwd / ".codex" / "skills" / "cortex-sync.md",
            cwd / ".codex" / "skills" / "cortex-sddwork.md",
        ]
        for legacy in legacy_paths:
            if legacy.exists():
                legacy.unlink()
                removed.append(str(legacy))

        # Drop empty Cortex-managed subdirectories.
        for subdir in (cwd / ".codex" / "agents", cwd / ".codex" / "skills"):
            if subdir.exists() and not any(subdir.iterdir()):
                subdir.rmdir()
                removed.append(str(subdir))

        return removed
