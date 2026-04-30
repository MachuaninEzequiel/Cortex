"""Tópico: Primeros Pasos."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel


class GettingStartedTopic:
    @property
    def title(self) -> str:
        return "Primeros Pasos"

    @property
    def icon(self) -> str:
        return "🚀"

    @property
    def one_liner(self) -> str:
        return "Cómo instalar y empezar a usar Cortex"

    @property
    def slug(self) -> str:
        return "start"

    @property
    def guide_path(self) -> str | None:
        return "docs/guides/getting-started.md"

    def render(self, console: Console) -> None:
        content = (
            "[bold yellow]1.[/] Activar tu entorno: [cyan]source .venv/bin/activate[/]  (o .venv\\Scripts\\Activate.ps1)\n"
            "[bold yellow]2.[/] Inicializar:        [cyan]cortex setup agent[/]\n"
            "[bold yellow]3.[/] Crear spec:         [cyan]cortex create-spec --title \"Mi Feature\"[/]\n"
            "[bold yellow]4.[/] Trabajar y guardar: [cyan]cortex save-session --title \"Mi Feature\"[/]\n"
            "[bold yellow]5.[/] Buscar contexto:    [cyan]cortex search \"mi query\"[/]\n"
            "[bold yellow]6.[/] Verificar salud:    [cyan]cortex doctor[/]\n"
            "\n"
            "[dim]Cortex se instala como dependencia en el .venv de tu propio proyecto.[/]\n"
            "[dim]Cada proyecto tiene su propio vault/ y .memory/ totalmente aislados.[/]\n"
            "\n"
            "📖 Guía completa: [link=docs/guides/getting-started.md]docs/guides/getting-started.md[/link]"
        )
        console.print(Panel(content, title="🚀 PRIMEROS PASOS", border_style="green", padding=(1, 2)))
