from __future__ import annotations

import shutil
from pathlib import Path

from cortex.ide.base import IDEAdapter

# Pi has no slash-skill distinction — every prompt lives under
# ``.pi/agents/`` regardless of whether it acts as a top-level anchor
# (cortex-sync, cortex-SDDwork, cortex-documenter) or as a subagent
# (cortex-code-*). Two sync lists keep both kinds aligned with their
# canonical source under ``.cortex/{skills,subagents}/``.

# Subagents — sourced from ``.cortex/subagents/<name>.md``. These are
# the Deep Track code-* helpers + the legacy documenter subagent (kept
# for backward compat, marked DEPRECATED).
_SHARED_SUBAGENTS = (
    "cortex-code-explorer.md",
    "cortex-code-implementer.md",
    "cortex-code-designer.md",
)

# Triadic anchors — sourced from ``.cortex/skills/<name>.md``. Phase 09.A+
# (May 2026): the three anchors land as ``agent`` files in the Pi bundle
# because Pi has no "skill" concept of its own. Their content is the
# canonical SKILL file (NOT the legacy subagent for the documenter).
_SHARED_SKILL_ANCHORS = (
    "cortex-sync.md",
    "cortex-SDDwork.md",
    "cortex-documenter.md",
)

# Legacy: keep the documenter SUBAGENT path also synced (with its
# DEPRECATED banner) so single-agent Pi flows that already reference the
# subagent keep working. The skill above is the canonical replacement.
_SHARED_LEGACY_SUBAGENTS = (
    "cortex-documenter.md",
)

# Backward-compat alias for the previous public name. Existing tests
# patch ``_SHARED_AGENTS`` — keep it pointing at the subagents list.
_SHARED_AGENTS = _SHARED_SUBAGENTS + _SHARED_LEGACY_SUBAGENTS


def _default_pi_bundle_dir() -> Path:
    """Path to the in-tree ``cortex-pi/`` bundle.

    Path(__file__) is cortex/ide/adapters/pi.py, so 4 parents up lands at
    the repo root that contains both ``cortex/`` and ``cortex-pi/``.
    """
    return Path(__file__).resolve().parent.parent.parent.parent / "cortex-pi"


class PiAdapter(IDEAdapter):
    @property
    def name(self) -> str:
        return "pi"

    @property
    def display_name(self) -> str:
        return "Pi Coding Agent"

    # ────────────────────────────────────────────────────────────────────────
    # DESACTIVADA (mayo 2026): Pi es ahora su propia SSoT.
    #
    # POR QUÉ ESTÁ COMENTADA:
    #   Esta función espejaba el contenido canónico de
    #   ``.cortex/{skills,subagents}/`` DENTRO de ``cortex-pi/.pi/agents/`` antes
    #   de copiar el bundle. Eso acoplaba el bundle de Pi a ``.cortex/``: cada
    #   inyección sobreescribía los agentes de Pi con la versión canónica, de
    #   modo que el bundle se "actualizaba" cada vez que cambiaba ``.cortex/``.
    #   Por decisión de diseño, el bundle ``cortex-pi/`` pasa a ser la ÚNICA
    #   fuente de verdad de Pi y NO debe mutar cuando ``.cortex/`` cambia.
    #
    # QUÉ HARÍA AL DESCOMENTAR:
    #   Volvería a sincronizar (sobrescribir) los 3 anchors triádicos
    #   (cortex-sync, cortex-SDDwork, cortex-documenter) desde
    #   ``.cortex/skills/`` y los 3 subagents code-* desde
    #   ``.cortex/subagents/`` hacia ``cortex-pi/.pi/agents/``, re-acoplando Pi
    #   al SSoT canónico. Si se descomenta, hay que reactivar TAMBIÉN su llamada
    #   en ``inject_profiles`` (abajo) y el flag ``sync_canonical`` en
    #   ``cortex/ide/__init__.py``.
    #
    # def sync_canonical_subagents(
    #     self,
    #     project_root: Path,
    #     *,
    #     bundle_dir: Path | None = None,
    # ) -> list[Path]:
    #     """Mirror ``.cortex/{skills,subagents}/`` into ``cortex-pi/.pi/agents/``.
    #
    #     Pi has no slash-skill concept of its own — every prompt is an
    #     ``agent`` under ``.pi/agents/``. Phase 09.A+ (May 2026) extends
    #     the original sync (which only covered the 3 code-* subagents) to
    #     also propagate the **three triadic anchors** (``cortex-sync``,
    #     ``cortex-SDDwork``, ``cortex-documenter``) from ``.cortex/skills/``.
    #     Without this extension the Pi bundle drifts from the SSoT every
    #     time the skills are updated upstream.
    #
    #     Sync sources, by priority:
    #
    #     - ``.cortex/skills/<anchor>.md``     → ``.pi/agents/<anchor>.md`` (anchor)
    #     - ``.cortex/subagents/<name>.md``    → ``.pi/agents/<name>.md`` (subagent)
    #
    #     The ``cortex-documenter.md`` entry comes from the SKILL (canonical
    #     closing anchor), NOT from the legacy subagent. The subagent file
    #     is irrelevant on Pi — Pi targets the skill content.
    #
    #     Idempotent. If the canonical directories do not exist (e.g. Pi
    #     is being injected before any Cortex setup ran), the bundle stays
    #     untouched and an empty list is returned.
    #
    #     Args:
    #         project_root: Project where the canonical files live.
    #         bundle_dir:   Override for the Pi bundle root. Tests pass a
    #                       temporary directory so they do not mutate the
    #                       repository's real ``cortex-pi/`` bundle.
    #
    #     Returns:
    #         Paths under ``<bundle_dir>/.pi/agents/`` that were overwritten.
    #     """
    #     from cortex.workspace.layout import WorkspaceLayout
    #
    #     layout = WorkspaceLayout.discover(project_root)
    #     skills_dir = layout.skills_dir
    #     subagents_dir = layout.subagents_dir
    #     if not skills_dir.is_dir() and not subagents_dir.is_dir():
    #         return []
    #
    #     bundle = bundle_dir if bundle_dir is not None else _default_pi_bundle_dir()
    #     pi_bundle_agents = bundle / ".pi" / "agents"
    #     pi_bundle_agents.mkdir(parents=True, exist_ok=True)
    #
    #     overwritten: list[Path] = []
    #
    #     # Skill anchors override anything in the subagents folder with
    #     # the same basename. Sync skills first so the documenter ends up
    #     # with the SKILL content (not the legacy DEPRECATED subagent).
    #     if skills_dir.is_dir():
    #         for name in _SHARED_SKILL_ANCHORS:
    #             src = skills_dir / name
    #             if not src.exists():
    #                 continue
    #             dst = pi_bundle_agents / name
    #             dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    #             overwritten.append(dst)
    #
    #     if subagents_dir.is_dir():
    #         for name in _SHARED_SUBAGENTS:
    #             src = subagents_dir / name
    #             if not src.exists():
    #                 continue
    #             dst = pi_bundle_agents / name
    #             dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    #             overwritten.append(dst)
    #
    #     return overwritten
    # ────────────────────────────────────────────────────────────────────────

    def inject_profiles(
        self,
        project_root: Path,
        prompts: dict[str, str] | None = None,
        *,
        sync_canonical: bool = True,
    ) -> list[str]:
        """Inject Cortex Pi configuration.

        Copies the entire cortex-pi folder contents into the project root,
        **as-is**. The bundle ``cortex-pi/`` is Pi's own single source of
        truth and is never refreshed from ``.cortex/`` — see the comment
        on the (disabled) ``sync_canonical_subagents`` method above.

        Args:
            project_root:   Destination project.
            prompts:        Unused by Pi (the bundle ships its own prompts).
            sync_canonical: NEUTRALIZED (mayo 2026). Kept in the signature
                            for backward compatibility with callers / the
                            CLI ``--no-sync-canonical`` flag, but it has no
                            effect: the bundle is always copied verbatim.
        """
        # Flag neutralizado: Pi ya no se rehidrata desde ``.cortex/``.
        # La llamada al sync queda comentada a propósito (la función fue
        # desactivada arriba). Para reactivar el acoplamiento canónico hay
        # que descomentar ``sync_canonical_subagents`` y esta línea.
        del sync_canonical  # acepta el kwarg pero lo ignora
        # if sync_canonical:
        #     self.sync_canonical_subagents(project_root)

        cortex_pi_dir = _default_pi_bundle_dir()

        files_written = []
        if cortex_pi_dir.exists() and cortex_pi_dir.is_dir():
            for item in cortex_pi_dir.iterdir():
                dest = project_root / item.name
                if item.is_dir():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                    files_written.append(f"{item.name}/")
                else:
                    shutil.copy2(item, dest)
                    files_written.append(item.name)
        else:
            raise FileNotFoundError(f"cortex-pi template directory not found at {cortex_pi_dir}")

        return files_written

    def get_config_paths(self) -> dict[str, Path]:
        """Pi configuration is project-local, no global config paths."""
        return {}
        
    def detect_installation(self) -> bool:
        """Detect if the Pi Coding Agent CLI is on PATH.

        Pi is distributed as the npm package ``@mariozechner/pi-coding-agent``.
        Once installed globally, it exposes a ``pi`` executable. We probe
        for that binary instead of returning a hardcoded ``True``, so
        ``cortex doctor`` and ``cortex inject --ide pi`` can surface a
        clear error when Pi is missing.
        """
        return shutil.which("pi") is not None

    def inject_mcp(self, project_root: Path) -> list[str]:
        """Pi Coding Agent uses bash tools, MCP injection not required."""
        return []

    def uninstall(self, project_root: Path | None = None) -> list[str]:
        """Uninstall Pi configuration."""
        if project_root is None:
            return []
            
        files_removed = []
        pi_dir = project_root / ".pi"
        if pi_dir.exists():
            shutil.rmtree(pi_dir)
            files_removed.append(".pi/")
            
        for f in ["AGENTS.md", "justfile", "README.md", "extensions"]:
            path = project_root / f
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                    files_removed.append(f"{f}/")
                else:
                    path.unlink()
                    files_removed.append(f)
                    
        return files_removed
