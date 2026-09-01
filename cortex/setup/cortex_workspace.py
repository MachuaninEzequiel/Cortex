"""
cortex.setup.cortex_workspace
-----------------------------
Generate the Cortex workspace structure used by Release 2:

- .cortex/system-prompt.md
- .cortex/skills/cortex-sync.md
- .cortex/skills/cortex-SDDwork.md
- .cortex/subagents/*.md
- .cortex/AGENT.md
- .cortex/workspace.yaml   (layout_version: 2)
"""

from __future__ import annotations


from pathlib import Path

_WORKSPACE_FILES_DIR = Path(__file__).resolve().parent / "workspace_files"


def _read_workspace_file(nombre: str) -> str:
    """Lee un archivo de workspace desde ``workspace_files/`` (fuente única V8).

    Los contenidos viven como archivos ``.md`` dentro del paquete; este
    módulo solo los sirve. Test de sincronía: tests/unit/setup/test_workspace_files_sync.py
    """
    return (_WORKSPACE_FILES_DIR / nombre).read_text(encoding="utf-8")


def _autopilot_skills_dir() -> Path:
    """Return the package directory containing Autopilot skill templates."""
    return Path(__file__).resolve().parent.parent / "autopilot" / "skills"


def render_system_prompt() -> str:
    return _read_workspace_file("system-prompt.md")


def render_agent_overview() -> str:
    return _read_workspace_file("agent-overview.md")


def render_cortex_sync_skill() -> str:
    return _read_workspace_file("cortex-sync.md")


def render_cortex_sddwork_skill() -> str:
    # Pluggable Middle (Phase 02 / T2.1): SDDwork emite checkpoints
    # (no YAML inline). El contrato compartido entre agentes Cortex es la
    # Session. El usuario cierra el ciclo con ``cortex finish-session``.
    # Mantenelo sincronizado con ``.cortex/skills/cortex-SDDwork.md``.
    return _read_workspace_file("cortex-SDDwork.md")


def render_cortex_documenter_skill() -> str:
    # Pluggable Middle (Phase 09.A+ / May 2026): /cortex-documenter is the
    # CLOSING ANCHOR of the triadic agent model (sync ↔ documenter as
    # mandatory anchors, middle pluggable). Mirrors
    # ``.cortex/skills/cortex-documenter.md`` byte-for-byte.
    return _read_workspace_file("cortex-documenter.md")


def render_subagent_explorer() -> str:
    # Pluggable Middle (Phase 02 / T2.2): emite checkpoint en lugar de YAML.
    # Mantenelo sincronizado con ``.cortex/subagents/cortex-code-explorer.md``.
    return _read_workspace_file("subagent-cortex-code-explorer.md")


def render_subagent_implementer() -> str:
    # Pluggable Middle (Phase 02 / T2.3): emite checkpoint en lugar de YAML.
    # Mantenelo sincronizado con ``.cortex/subagents/cortex-code-implementer.md``.
    return _read_workspace_file("subagent-cortex-code-implementer.md")


def render_subagent_documenter() -> str:
    # Pluggable Middle (Phase 01 / T1.8): documenter accepts two operating
    # modes — Reconstruction (via cortex_finish_session) and Legacy YAML.
    # The full prompt lives at ``.cortex/subagents/cortex-documenter.md`` and
    # is rendered verbatim here. Update both files when editing.
    #
    # Phase 09.A+ (May 2026): this subagent is now DEPRECATED in favour of
    # the canonical /cortex-documenter skill. Kept only for single-agent
    # IDEs (Codex / cortex-pi) without slash-skill dispatch. The DEPRECATED
    # banner below renders verbatim into the installed file so the LLM
    # reading the prompt knows to prefer the skill when available.
    return _read_workspace_file("subagent-cortex-documenter.md")


def render_subagent_designer() -> str:
    # Pluggable Middle Phase 09.B: cortex-code-designer subagent. Lives
    # between explorer and implementer in Deep Track. Produces the design
    # doc at ``vault/designs/<session_id>.md`` and emits a checkpoint.
    # Keep this string byte-identical to
    # ``.cortex/subagents/cortex-code-designer.md``.
    return _read_workspace_file("subagent-cortex-code-designer.md")


def _obsidian_skill_files() -> dict[str, str]:
    """Return the Obsidian formatting skills, hardcoded into ``.cortex/``.

    DESACOPLE bundle↔canonical (mayo 2026): antes estas skills se LEÍAN
    del bundle de Pi (``cortex-pi/.pi/skills/obsidian{,-index}/``), lo que
    acoplaba ``.cortex/`` al bundle. Ahora ``.cortex/`` es autosuficiente:
    el contenido vive embebido acá y el bundle de Pi conserva su propia
    copia independiente (Pi es su propia SSoT). Estas skills de referencia
    son estables y no cambian, así que la duplicación no genera deuda real.

    Se instalan bajo ``.cortex/skills/obsidian{,-index}/`` para que
    ``/cortex-documenter`` (y el resto de IDEs) puedan referenciarlas al
    escribir notas en el Vault.

    Returns a mapping ``{ ".cortex/skills/<path>.md": content }`` — same
    shape ``workspace_file_map`` consumed before, so callers don't change.
    """
    obsidian_markdown = _read_workspace_file("obsidian-obsidian_markdown.md")

    obsidian_bases = _read_workspace_file("obsidian-obsidian_bases.md")

    json_canvas = _read_workspace_file("obsidian-json_canvas.md")

    defuddle = _read_workspace_file("obsidian-defuddle.md")

    obsidian_index = _read_workspace_file("obsidian-obsidian_index.md")

    return {
        ".cortex/skills/obsidian/obsidian-markdown.md": obsidian_markdown,
        ".cortex/skills/obsidian/obsidian-bases.md": obsidian_bases,
        ".cortex/skills/obsidian/json-canvas.md": json_canvas,
        ".cortex/skills/obsidian/defuddle.md": defuddle,
        ".cortex/skills/obsidian-index/SKILL.md": obsidian_index,
    }


def workspace_file_map() -> dict[str, str]:
    from cortex.setup.templates import render_workspace_yaml

    base = {
        ".cortex/system-prompt.md": render_system_prompt(),
        ".cortex/AGENT.md": render_agent_overview(),
        ".cortex/workspace.yaml": render_workspace_yaml(),
        ".cortex/skills/cortex-sync.md": render_cortex_sync_skill(),
        ".cortex/skills/cortex-SDDwork.md": render_cortex_sddwork_skill(),
        ".cortex/skills/cortex-documenter.md": render_cortex_documenter_skill(),
        ".cortex/subagents/cortex-code-explorer.md": render_subagent_explorer(),
        ".cortex/subagents/cortex-code-implementer.md": render_subagent_implementer(),
        ".cortex/subagents/cortex-code-designer.md": render_subagent_designer(),
        ".cortex/subagents/cortex-documenter.md": render_subagent_documenter(),
        # Pluggable Middle, Phase 00 / T0.11.
        # Sessions directory is created here even though no concrete files
        # are written yet — ``cortex create-spec`` will populate it. The
        # ``.gitkeep`` lets the empty directory survive a fresh ``git clone``.
        ".cortex/sessions/.gitkeep": "",
    }
    # Phase 09.A+ — install Obsidian formatting reference skills so the
    # /cortex-documenter skill can ground its Markdown output in the
    # Obsidian conventions the vault expects. Hardcoded into ``.cortex/``
    # (mayo 2026): ya NO se leen del bundle de Pi — ``.cortex/`` es
    # autosuficiente y el bundle ``cortex-pi/`` es su propia SSoT.
    base.update(_obsidian_skill_files())
    return base


def autopilot_file_map() -> dict[str, str]:
    """Return Autopilot skill files to install into the workspace.

    Reads ``*.md`` from the package ``cortex/autopilot/skills/`` directory.
    """
    skills_dir = _autopilot_skills_dir()
    files: dict[str, str] = {}
    if skills_dir.exists():
        for skill_path in sorted(skills_dir.glob("*.md")):
            content = skill_path.read_text(encoding="utf-8")
            files[f".cortex/skills/{skill_path.name}"] = content
    return files


def ensure_cortex_workspace(
    root: str | Path, *, overwrite: bool = False, autopilot: bool = False
) -> dict[str, list[str]]:
    """
    Create the Release 2 Cortex workspace files inside ``root``.

    Args:
        autopilot: When ``True``, also install Autopilot skills into
            ``.cortex/skills/``.  Normal setup is unaffected when ``False``.
    """
    base = Path(root)
    created: list[str] = []
    skipped: list[str] = []

    files = workspace_file_map()
    if autopilot:
        files.update(autopilot_file_map())

    for relative, content in files.items():
        path = base / relative
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.exists() and not overwrite:
            skipped.append(relative)
            continue

        path.write_text(content, encoding="utf-8")
        created.append(relative)

    return {"created": created, "skipped": skipped}
