"""
cortex.tutor.hint
-----------------
Contextual hint engine that inspects the current project state
and suggests the most relevant next action. Zero tokens consumed.

EPIC 6: Uses WorkspaceLayout for path detection so both new
and legacy layouts work correctly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from cortex.workspace.layout import WorkspaceLayout


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class Hint:
    """A single contextual tip."""

    icon: str
    title: str
    body: str
    command: str

    def render(self, console: Console | None = None) -> None:
        """Render the hint as a rich panel."""
        from cortex.tutor.engine import _safe_console

        c = console or _safe_console()
        content = f"{self.body}\n\n  [bold cyan]$ {self.command}[/]"
        c.print()
        c.print(Panel(content, title=f"{self.icon} {self.title}", border_style="cyan", padding=(1, 2)))
        c.print()


@dataclass
class ProjectState:
    """Detected state of the current project directory."""

    has_config: bool = False
    has_vault: bool = False
    has_cortex_dir: bool = False
    has_org_yaml: bool = False
    has_memory: bool = False
    has_specs: bool = False
    has_sessions: bool = False
    has_enterprise_vault: bool = False
    spec_count: int = 0
    session_count: int = 0
    vault_doc_count: int = 0
    has_github_workflows: bool = False
    has_mcp_config: bool = False

    @classmethod
    def detect(cls, project_root: Path) -> "ProjectState":
        """Inspect the filesystem at project_root and build state.

        Uses WorkspaceLayout to resolve paths so both new and legacy
        layouts are detected correctly.
        """
        state = cls()
        layout = WorkspaceLayout.discover(project_root)

        state.has_config = layout.config_path.exists()
        state.has_vault = layout.vault_path.is_dir()
        state.has_cortex_dir = layout.workspace_root.exists()
        state.has_org_yaml = layout.org_config_path.exists()
        state.has_memory = layout.episodic_memory_path.is_dir()
        state.has_enterprise_vault = layout.enterprise_vault_path.is_dir()
        state.has_github_workflows = layout.workflows_dir.is_dir()

        # Count specs
        specs_dir = layout.vault_path / "specs"
        if specs_dir.is_dir():
            spec_files = list(specs_dir.glob("*.md"))
            state.spec_count = len(spec_files)
            state.has_specs = state.spec_count > 0

        # Count sessions
        sessions_dir = layout.vault_path / "sessions"
        if sessions_dir.is_dir():
            session_files = list(sessions_dir.glob("*.md"))
            state.session_count = len(session_files)
            state.has_sessions = state.session_count > 0

        # Count total vault docs
        if state.has_vault:
            state.vault_doc_count = len(list(layout.vault_path.rglob("*.md")))

        # Detect MCP config (any of the common locations)
        mcp_locations = [
            project_root / ".mcp.json",
            project_root / ".vscode" / "mcp.json",
            Path.home() / ".cursor" / "mcp.json",
        ]
        state.has_mcp_config = any(p.exists() for p in mcp_locations)

        return state


# ---------------------------------------------------------------------------
# Hint engine
# ---------------------------------------------------------------------------


class HintEngine:
    """Generates contextual tips based on project state.

    Tips are ordered by priority: the first matching condition wins.
    """

    def get_hint(self, state: ProjectState) -> Hint:
        """Return the most relevant hint for the current state."""
        hints: list[tuple[bool, Hint]] = [
            # Level 0: Not initialized
            (
                not state.has_config,
                Hint(
                    icon="🚀",
                    title="Cortex no está inicializado en este proyecto",
                    body="Este directorio no tiene config.yaml.\nInicializá Cortex para empezar a construir memoria.",
                    command="cortex setup agent",
                ),
            ),
            # Level 1: Initialized but no specs
            (
                state.has_config and not state.has_specs,
                Hint(
                    icon="📝",
                    title="No hay especificaciones creadas",
                    body="Antes de codear, creá una spec para documentar qué vas a hacer.\nEsto alimenta el contexto para futuras búsquedas.",
                    command='cortex create-spec --title "Mi Feature" --goal "Descripción del objetivo"',
                ),
            ),
            # Level 2: Has specs but no sessions
            (
                state.has_specs and not state.has_sessions,
                Hint(
                    icon="💾",
                    title=f"Tenés {state.spec_count} spec(s) pero 0 sesiones guardadas",
                    body="Después de trabajar, guardá tu sesión para alimentar la memoria.\nCortex usa estas sesiones para dar contexto en tareas futuras.",
                    command='cortex save-session --title "Mi Sesión" --spec-summary "Lo que hice"',
                ),
            ),
            # Level 3: Has content but no pipeline
            (
                state.vault_doc_count > 5 and not state.has_github_workflows,
                Hint(
                    icon="⚙️",
                    title="Tu vault está creciendo pero no tenés pipeline CI",
                    body="Configurá el pipeline DevSecDocOps para proteger la calidad\nautomáticamente en cada PR.",
                    command="cortex setup pipeline",
                ),
            ),
            # Level 4: All local, no enterprise
            (
                state.vault_doc_count > 10 and not state.has_org_yaml,
                Hint(
                    icon="🏢",
                    title="Tu knowledge base tiene sustancia. ¿Trabajás en equipo?",
                    body="Podés compartir conocimiento con la capa enterprise.\nEsto permite retrieval cruzado entre proyectos.",
                    command="cortex setup enterprise --preset small-company",
                ),
            ),
            # Level 5: Enterprise configured, no promotions yet
            (
                state.has_org_yaml and not state.has_enterprise_vault,
                Hint(
                    icon="📤",
                    title="Enterprise configurado pero sin conocimiento promovido",
                    body="Revisá qué docs están listos para promover al vault corporativo.\nUsá --dry-run para ver el plan sin ejecutar.",
                    command="cortex promote-knowledge --dry-run",
                ),
            ),
            # Level 6: No IDE configured
            (
                state.has_config and not state.has_mcp_config,
                Hint(
                    icon="🔌",
                    title="Cortex no está conectado a ningún IDE",
                    body="Conectá tu IDE para que el agente de IA use herramientas Cortex\n(búsqueda, specs, sessions) directamente.",
                    command="cortex inject",
                ),
            ),
            # Level 7: Everything looks good
            (
                True,
                Hint(
                    icon="✅",
                    title="Tu proyecto Cortex está en buena forma",
                    body=(
                        f"Vault: {state.vault_doc_count} docs | "
                        f"Specs: {state.spec_count} | "
                        f"Sessions: {state.session_count}\n"
                        "Buscá algo en tu memoria para verificar que todo funciona."
                    ),
                    command='cortex search "mi query"',
                ),
            ),
        ]

        for condition, hint in hints:
            if condition:
                return hint

        # Unreachable — the last entry always matches
        return hints[-1][1]  # pragma: no cover
