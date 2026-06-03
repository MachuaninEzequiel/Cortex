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

import os
import re
import shutil
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

# Marcadores para la entrada de trust en el config GLOBAL ``~/.codex/config.toml``.
# Codex DESCARTA toda la capa project-local ``.codex/`` (incluido nuestro MCP
# server) hasta que el proyecto esta "trusted" alli — confirmado en los logs de
# ``codex_app_server`` ("Project-local config, hooks, and exec policies are
# disabled ... until the project is trusted"). Se agrega una entrada de trust
# por proyecto, envuelta en marcadores ESPECIFICOS del path para que
# ``uninstall`` remueva solo la de ese proyecto (multi-repo safe).
_CORTEX_TRUST_MARKER_OPEN_TPL = "# BEGIN CORTEX TRUST [{tag}] (auto-generated, do not edit)"
_CORTEX_TRUST_MARKER_CLOSE_TPL = "# END CORTEX TRUST [{tag}]"


def _build_cortex_agents_section(autogen_header: str) -> str:
    """Build the Cortex block injected into AGENTS.md at the project root.

    Phase 09.A+ / May 2026 — rewritten for the **triadic anchor model**:

        /cortex-sync       (mandatory opening anchor)
            ↓
        MIDDLE (pluggable: cortex-SDDwork / BYO / etc.)
            ↓
        /cortex-documenter (mandatory closing anchor)

    Codex has no native ``Task`` tool for parallel subagent delegation
    and no native slash-skill dispatch. The single Codex agent therefore
    executes the three anchors **in sequence within the same session**,
    guided by the explicit phase instructions below. Each anchor uses
    the MCP tools documented in the corresponding canonical skill file
    under ``.cortex/skills/``.
    """
    return f"""{_CORTEX_AGENTS_MD_MARKER_OPEN}
<!--
{autogen_header.strip()}
-->

# Cortex Workflow for Codex (triadic anchors, single-agent sequential)

This project uses **Cortex** governance. Cortex is structured around
three slash-invocable anchors:

| Anchor             | Role            | Mandatory |
|--------------------|-----------------|-----------|
| `/cortex-sync`     | opening anchor  | YES — every Session opens here |
| (middle)           | implementation  | pluggable (SDDwork / BYO / etc.) |
| `/cortex-documenter` | closing anchor | YES — every Session closes here |

Codex has no native `Task` tool nor slash-skill dispatch, so the **single
Codex agent executes the three phases sequentially within the same
session**, guided by the explicit instructions below. The phases mirror
the canonical skill files under `.cortex/skills/`.

## Pre-flight check (mandatory, every session)

Before any operation, call `cortex_ping`. If the response is not
`status: "ok"`, abort the operation with a clear message to the user:

> The Cortex MCP server is unavailable (status: <status>; last_error:
> <error>). Restart the IDE or run `cortex doctor` to diagnose.

NEVER fall back to manual markdown writing. NEVER degrade Cortex features
when the MCP is down.

---

## Phase 1 — Opening anchor (acts as `/cortex-sync`)

Mandatory first step. See `.cortex/skills/cortex-sync.md` for the full
canonical skill.

1. Call `cortex_sync_ticket` with the user's request. The MCP server
   rejects any later `cortex_create_spec` if this step is skipped.
2. Read `CONTEXT.md` if it exists; its terms are canonical and the spec
   must not invent synonyms.
3. Explore the repo with `glob` + `read` (NOT modify) to ground the spec
   in real code.
4. Emit a proposal with `cortex_emit_proposal` (summary + 2-5
   alternatives + recommendation + risks). In `proposal_mode="required"`,
   end the turn after emitting — wait for the user's confirmation in a
   later message before continuing.
5. After confirmation, call `cortex_create_spec` (passing
   `proposal_mode` / `proposal_confirmed` as appropriate). This persists
   the spec to `vault/specs/` AND opens the Session.

---

## Phase 2 — Middle (acts as `/cortex-SDDwork`)

Implement the persisted spec. The full canonical skill lives at
`.cortex/skills/cortex-SDDwork.md`.

1. Verify the active Session with `cortex_session_status`. Abort if no
   active session exists.
2. Decide between **Fast Track** (1-2 files, cosmetic / bugfix / simple
   logic) and **Deep Track** (refactors, new architecture).
3. Make the changes following existing repo conventions. Run tests if
   declared in the spec's `verification_hooks`. Codex cannot delegate to
   subagents — for Deep Track, perform the explorer / designer /
   implementer steps sequentially in your own context.
4. Emit ONE `cortex_session_checkpoint` with `source="cortex-SDDwork"`,
   carrying `verified_claims`, `unverified_claims`, `artifacts_touched`,
   and a brief `note`. Do NOT close the session here — that's Phase 3.

---

## Phase 3 — Closing anchor (acts as `/cortex-documenter`)

Mandatory final step. The full canonical skill lives at
`.cortex/skills/cortex-documenter.md`. The documenter writes the session
note **by hand with editorial criterion** — NOT a template fill.

1. Call `cortex_documenter_briefing` (no args = active session). Receive
   JSON with: spec, diff_text, diff_entries, files_verified_by_git (✓),
   files_declared_only (◌), in_scope / out_of_scope / unimplemented
   files, verification_results, contradictions, suggested_adrs,
   raw_checkpoints, gitless flag.
2. Apply the canonical decision table to decide what doc types to emit
   (1 mandatory main note: `session` or `handoff`; 0..N optional:
   `adr`, `decision`, `incident`, `postmortem`, `runbook`,
   `architecture`, `changelog`, `glossary`, `hu`). See the skill file
   for the objective criteria per doc type.
3. Write the main note body in your own prose — reference, don't
   duplicate. Mention files with provenance: ``✓ path`` for git-verified,
   ``◌ path`` for declared-only (uncommitted).
4. **Recommended**: call `cortex_self_review_note(body=<draft>,
   verification_hooks_passed=<bool>)`. Surfaces placeholder tokens and
   hollow success claims. Revise or proceed.
5. Persist the main note with `cortex_write_doc(doc_type=...,
   payload=...)`. Persist any secondary notes the same way.
6. Close the Session with `cortex_close_session(status=...,
   session_note_path=..., adrs_created=[...])`. `status` MUST be one of
   `closed` / `handoff` / `abandoned`. Use `handoff` (not `closed`) when
   required verification hooks failed OR unimplemented files remain.

---

## Hard rules

- NEVER call `cortex_create_spec` before `cortex_sync_ticket`. The MCP
  server rejects it with a governance violation.
- NEVER skip Phase 3 (closing anchor). A session without the documenter
  closing step erodes the organizational memory.
- NEVER write Markdown to the vault by hand with `write_file` — the
  canonical routing depends on `cortex_write_doc` and `cortex_create_spec`.
- The status `handoff` is a first-class outcome. If hooks fail or
  unimplemented files remain, close with `handoff` (NOT `closed`).
- If `CONTEXT.md` exists at project root or under `.cortex/CONTEXT.md`,
  treat its terms as canonical. Add new canonical terms via
  `cortex_write_doc(doc_type="glossary", ...)`.

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
        # Replacement vía callable: evita que ``re.sub`` interprete backslashes
        # del bloque (rutas Windows) como escapes de regex.
        return pattern.sub(lambda _m: cortex_block.strip(), existing)
    # Append: separator only if existing has content and doesn't end with newline
    sep = "" if not existing else ("\n" if existing.endswith("\n") else "\n\n")
    return existing + sep + cortex_block


def _resolve_cortex_command() -> str:
    """Ruta absoluta al ejecutable ``cortex``, o el nombre pelado como fallback.

    Codex spawnea el MCP server heredando el entorno con que fue lanzado. En
    Windows — sobre todo la app Codex Desktop — ese entorno puede NO incluir el
    directorio ``Scripts`` de Python en el ``PATH``, con lo cual un ``"cortex"``
    pelado no resolveria. Capturar la ruta absoluta en tiempo de instalacion
    elimina esa ambiguedad.
    """
    return shutil.which("cortex") or "cortex"


def _build_cortex_toml_block(project_root: Path) -> str:
    """Devuelve el bloque TOML de configuracion del MCP server Cortex.

    Sintaxis validada contra https://developers.openai.com/codex/mcp:

        [mcp_servers.cortex]
        command = "<ruta absoluta a cortex>"
        args = ["mcp-server", "--stdio", "--project-root", "<path>"]
        startup_timeout_sec = 60
        enabled = true

        [mcp_servers.cortex.env]
        PYTHONWARNINGS = "ignore"
        PYTHONIOENCODING = "utf-8"
        PYTHONUNBUFFERED = "1"

    Hardening (2026-05-30):

    - ``command`` se resuelve a ruta absoluta (Codex Desktop no garantiza el
      PATH de la shell del usuario).
    - ``startup_timeout_sec = 60``: el server Python es pesado en frio y el
      default de Codex (10 s) lo mata. El propio ``node_repl`` de OpenAI usa
      120 s; 60 s es margen holgado.
    - ``PYTHONIOENCODING`` / ``PYTHONUNBUFFERED`` protegen el stdio JSON-RPC en
      Windows.

    Los strings se escapan para backslashes de Windows.
    """
    project_str = str(project_root).replace("\\", "\\\\")
    command_str = _resolve_cortex_command().replace("\\", "\\\\")
    return f"""{_CORTEX_TOML_MARKER_OPEN}
[mcp_servers.cortex]
command = "{command_str}"
args = ["mcp-server", "--stdio", "--project-root", "{project_str}"]
startup_timeout_sec = 60
enabled = true

[mcp_servers.cortex.env]
PYTHONWARNINGS = "ignore"
PYTHONIOENCODING = "utf-8"
PYTHONUNBUFFERED = "1"
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
        # Replacement vía callable: el bloque trae rutas Windows con backslashes
        # que ``re.sub`` interpretaria como escapes de regex en un repl string.
        return pattern.sub(lambda _m: cortex_toml.strip(), existing)
    sep = "" if not existing else ("\n" if existing.endswith("\n") else "\n\n")
    return existing + sep + cortex_toml


# ---------------------------------------------------------------------------
# Trust del proyecto en el config GLOBAL (~/.codex/config.toml)
# ---------------------------------------------------------------------------


def _codex_global_config_path() -> Path:
    """Resuelve el ``config.toml`` GLOBAL de Codex (respeta ``CODEX_HOME``).

    Codex lee de este archivo, de forma incondicional, tanto los MCP servers
    como el trust de proyectos. Default ``~/.codex/config.toml``; la env var
    ``CODEX_HOME`` redefine el directorio (Codex la respeta, y los tests la
    usan para aislamiento).
    """
    codex_home = os.environ.get("CODEX_HOME")
    base = Path(codex_home) if codex_home else (Path.home() / ".codex")
    return base / "config.toml"


def _trust_markers(project_root: Path) -> tuple[str, str]:
    """Marcadores BEGIN/END especificos del path para la entrada de trust."""
    tag = str(project_root)
    return (
        _CORTEX_TRUST_MARKER_OPEN_TPL.format(tag=tag),
        _CORTEX_TRUST_MARKER_CLOSE_TPL.format(tag=tag),
    )


def _build_cortex_trust_block(project_root: Path) -> str:
    """Entrada de trust para el config global, envuelta en marcadores del path.

    Sintaxis (a confirmar contra la version instalada de Codex; validado contra
    el mensaje de ``codex_app_server`` que pide "add <path> as a trusted
    project in ~/.codex/config.toml"):

        [projects."<path>"]
        trust_level = "trusted"
    """
    open_m, close_m = _trust_markers(project_root)
    project_str = str(project_root).replace("\\", "\\\\")
    return f"""{open_m}
[projects."{project_str}"]
trust_level = "trusted"
{close_m}
"""


def _global_has_foreign_trust(content: str, project_root: Path) -> bool:
    """¿Existe ya un ``[projects."<este path>"]`` FUERA de nuestros marcadores?

    Si el usuario (o Codex) ya confio el proyecto por su cuenta, NO debemos
    agregar otra tabla con la misma key: TOML prohibe tablas duplicadas y
    romperia el parseo de toda la config. La comparacion normaliza
    case/separadores (Windows es case-insensitive).
    """
    target = os.path.normcase(os.path.normpath(str(project_root)))
    for match in re.finditer(
        r"""(?mi)^\s*\[projects\.(?:"([^"]*)"|'([^']*)')\]\s*$""", content
    ):
        key = match.group(1) if match.group(1) is not None else match.group(2)
        # Los basic strings escapan backslashes (\\ -> \); los literales no.
        key_unescaped = key.replace("\\\\", "\\")
        if os.path.normcase(os.path.normpath(key_unescaped)) == target:
            return True
    return False


def _merge_trust_into_global(existing: str, project_root: Path) -> str:
    """Merge no-destructivo del trust de ESTE proyecto en el config global.

    Agrega/reemplaza SOLO el bloque entre nuestros marcadores (especificos del
    path), preservando todo lo demas: ``marketplaces``, ``plugins``, otros MCP
    servers, ``desktop`` y otros proyectos confiados. Idempotente.

    Si el proyecto ya esta confiado fuera de nuestros marcadores, no toca nada
    (evita una tabla ``[projects."..."]`` duplicada que invalidaria el TOML).
    """
    open_m, close_m = _trust_markers(project_root)
    pattern = re.compile(
        re.escape(open_m) + r".*?" + re.escape(close_m) + r"\n?",
        re.DOTALL,
    )
    ours_present = bool(pattern.search(existing))
    without_ours = pattern.sub("", existing)

    if _global_has_foreign_trust(without_ours, project_root):
        # Ya confiado por el usuario/Codex: no duplicar. Si nosotros habiamos
        # agregado el bloque, lo quitamos para no dejar la tabla duplicada.
        return without_ours if ours_present else existing

    trust_block = _build_cortex_trust_block(project_root)
    if ours_present:
        # Replacement vía callable: el path del proyecto trae backslashes.
        return pattern.sub(lambda _m: trust_block.strip() + "\n", existing)
    sep = "" if not existing else ("\n" if existing.endswith("\n") else "\n\n")
    return existing + sep + trust_block


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
                ".cortex/skills/cortex-documenter.md",
                ".cortex/subagents/cortex-code-explorer.md",
                ".cortex/subagents/cortex-code-implementer.md",
                ".cortex/subagents/cortex-code-designer.md",
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
        """Inyectar el MCP server Cortex para Codex (modelo mono-repo).

        Dos escrituras, ambas merge **no-destructivo**:

        1. ``<proyecto>/.codex/config.toml`` — registro project-scoped del MCP.
           Solo activo en este proyecto (mono-repo). Sintaxis validada contra
           https://developers.openai.com/codex/mcp.
        2. ``~/.codex/config.toml`` (global) — marca el proyecto como
           ``trusted``. Sin esto Codex DESCARTA en silencio toda la capa
           project-local (incluido el MCP) hasta confiar el proyecto. Se
           preserva intacto el resto del config global del usuario.
        """
        paths = self.get_config_paths()
        written: list[str] = []

        # 1. Registro project-scoped del MCP (mono-repo).
        config_path = project_root / paths["config_toml"]
        config_path.parent.mkdir(parents=True, exist_ok=True)
        cortex_toml = _build_cortex_toml_block(project_root)
        existing = ""
        if config_path.exists():
            _backup_file(config_path)
            existing = config_path.read_text(encoding="utf-8")
        config_path.write_text(
            _replace_or_append_cortex_toml_block(existing, cortex_toml),
            encoding="utf-8",
        )
        written.append(str(config_path))

        # 2. Trust del proyecto en el config global (habilita la capa
        #    project-local para que Codex efectivamente cargue el MCP).
        global_path = _codex_global_config_path()
        global_existing = (
            global_path.read_text(encoding="utf-8") if global_path.exists() else ""
        )
        new_global = _merge_trust_into_global(global_existing, project_root)
        if new_global != global_existing:
            global_path.parent.mkdir(parents=True, exist_ok=True)
            if global_path.exists():
                _backup_file(global_path)
            global_path.write_text(new_global, encoding="utf-8")
            written.append(str(global_path))
            self._print_trust_notice(project_root, global_path)

        return written

    @staticmethod
    def _print_trust_notice(project_root: Path, global_path: Path) -> None:
        """Aviso explicito y auditable: marcamos el proyecto como trusted."""
        print(
            "\n[Cortex][Codex] Proyecto marcado como 'trusted' en Codex:\n"
            f"    {project_root}\n"
            f"  escrito en: {global_path}\n"
            "  Necesario para que Codex cargue el MCP server (sin trust, Codex\n"
            "  ignora la capa project-local .codex/). Esto habilita la capa\n"
            "  project-local (config/hooks/exec policies) SOLO para este\n"
            "  proyecto. Se revierte con 'cortex uninstall --ide codex'.\n"
        )

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

        # 2b. Revertir la entrada de trust de ESTE proyecto en el config global
        # (ownership-aware: solo el bloque entre NUESTROS marcadores para este
        # path). No toca el trust de otros proyectos ni un trust que el usuario
        # haya puesto a mano fuera de los marcadores.
        global_path = _codex_global_config_path()
        if global_path.exists():
            existing = global_path.read_text(encoding="utf-8")
            open_m, close_m = _trust_markers(cwd)
            trust_pattern = re.compile(
                re.escape(open_m) + r".*?" + re.escape(close_m) + r"\n?",
                re.DOTALL,
            )
            cleaned = trust_pattern.sub("", existing)
            if cleaned != existing:
                _backup_file(global_path)
                global_path.write_text(cleaned.rstrip() + "\n", encoding="utf-8")
                removed.append(f"{global_path} (Cortex trust entry removed)")

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
