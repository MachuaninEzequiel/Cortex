"""
cortex.tutor.engine
-------------------
TUI engine for the interactive Cortex tutor.
Handles menu rendering, topic navigation, and the main loop.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Protocol

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def _safe_console() -> Console:
    """Create a Console that works on Windows with emoji support.

    On Windows legacy terminals (cp1252), rich's default renderer
    cannot encode emoji. We switch the console codepage to UTF-8
    and wrap stdout to handle encoding gracefully.
    """
    if sys.platform == "win32":
        # Switch console output codepage to UTF-8
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)  # type: ignore[union-attr]
        except Exception:
            pass

        # Wrap stdout in a UTF-8 writer to prevent charmap errors
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

        return Console(force_terminal=True, force_jupyter=False)
    return Console()


# ---------------------------------------------------------------------------
# Topic protocol — every topic module must satisfy this contract
# ---------------------------------------------------------------------------


class TutorTopic(Protocol):
    """Contract that each tutor topic must implement."""

    @property
    def title(self) -> str:
        """Short title for the menu (e.g. 'Pipeline CI/CD')."""
        ...

    @property
    def icon(self) -> str:
        """Emoji icon for the menu entry."""
        ...

    @property
    def one_liner(self) -> str:
        """One-line description shown in the menu."""
        ...

    @property
    def slug(self) -> str:
        """Machine-readable name for direct access (e.g. 'pipeline')."""
        ...

    @property
    def guide_path(self) -> str | None:
        """Relative path to the extended guide in docs/guides/, or None."""
        ...

    def render(self, console: Console) -> None:
        """Render the topic content to the console (max 20-25 lines)."""
        ...


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


@dataclass
class TutorEngine:
    """Interactive TUI engine for the Cortex tutor.

    Manages a registry of topics and provides a navigable menu
    with numbered selection and direct topic access by slug.
    """

    console: Console = field(default_factory=_safe_console)
    topics: list[TutorTopic] = field(default_factory=list)

    def register(self, topic: TutorTopic) -> None:
        """Register a navigable topic."""
        self.topics.append(topic)

    # -- Menu ---------------------------------------------------------------

    def _render_menu(self) -> None:
        """Render the main menu with all registered topics."""
        self.console.clear()

        title_text = Text()
        title_text.append("🧠 CORTEX TUTOR", style="bold cyan")
        title_text.append(" — Guía Offline Interactiva", style="dim")

        table = Table(
            show_header=False,
            box=None,
            padding=(0, 2),
            expand=True,
        )
        table.add_column("Nro", style="bold yellow", width=4)
        table.add_column("Icon", width=3)
        table.add_column("Tópico", style="bold white")
        table.add_column("Descripción", style="dim")

        for i, topic in enumerate(self.topics, 1):
            table.add_row(f" {i}.", topic.icon, topic.title, topic.one_liner)

        self.console.print()
        self.console.print(
            Panel(
                table,
                title=str(title_text),
                subtitle="[dim]q = salir | número = ver tópico[/dim]",
                border_style="cyan",
                padding=(1, 2),
            )
        )
        self.console.print()

    # -- Topic display ------------------------------------------------------

    def show_topic(self, index: int) -> None:
        """Render a single topic by its 0-based index."""
        if 0 <= index < len(self.topics):
            self.console.clear()
            self.topics[index].render(self.console)

    def show_topic_by_slug(self, slug: str) -> bool:
        """Render a topic by its slug name. Returns True if found."""
        slug_lower = slug.lower().strip()
        for topic in self.topics:
            if topic.slug == slug_lower:
                topic.render(self.console)
                return True
        return False

    # -- Navigation footer --------------------------------------------------

    def _render_footer(self) -> None:
        """Render the navigation footer after a topic."""
        self.console.print()
        self.console.print(
            "[dim]  ← Enter = volver al menú  |  q = salir[/dim]"
        )

    # -- Main loop ----------------------------------------------------------

    def run(self) -> None:
        """Start the interactive TUI loop."""
        if not self.topics:
            self.console.print("[red]No hay tópicos registrados.[/red]")
            return

        while True:
            self._render_menu()
            try:
                choice = input("  Elegí un tema (1-{}) o 'q' para salir: ".format(len(self.topics)))
            except (EOFError, KeyboardInterrupt):
                self.console.print()
                break

            choice = choice.strip().lower()

            if choice in ("q", "quit", "exit", "salir"):
                self.console.print("\n  [cyan]¡Hasta la próxima![/cyan]\n")
                break

            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(self.topics):
                    self.show_topic(idx)
                    self._render_footer()
                    try:
                        input()
                    except (EOFError, KeyboardInterrupt):
                        break
                    continue

            # Try slug match
            if self.show_topic_by_slug(choice):
                self._render_footer()
                try:
                    input()
                except (EOFError, KeyboardInterrupt):
                    break
                continue

            self.console.print(f"  [red]'{choice}' no es válido.[/red] Usá un número (1-{len(self.topics)}) o 'q'.")
            try:
                input("  [Enter para continuar]")
            except (EOFError, KeyboardInterrupt):
                break

    # -- Factory ------------------------------------------------------------

    @classmethod
    def default(cls) -> "TutorEngine":
        """Create an engine pre-loaded with all built-in topics."""
        from cortex.tutor.topics import get_all_topics

        engine = cls()
        for topic in get_all_topics():
            engine.register(topic)
        return engine
