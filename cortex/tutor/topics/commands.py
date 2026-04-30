"""Tópico: Comandos Esenciales."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


class CommandsTopic:
    @property
    def title(self) -> str:
        return "Comandos Esenciales"

    @property
    def icon(self) -> str:
        return "📋"

    @property
    def one_liner(self) -> str:
        return "Cheatsheet rápido de los comandos más usados"

    @property
    def slug(self) -> str:
        return "commands"

    @property
    def guide_path(self) -> str | None:
        return None

    def render(self, console: Console) -> None:
        table = Table(
            show_header=True,
            header_style="bold cyan",
            border_style="dim",
            padding=(0, 1),
            expand=True,
        )
        table.add_column("Comando", style="bold white", min_width=22)
        table.add_column("Para qué sirve", style="dim")

        commands = [
            ("cortex setup agent", "Inicializar Cortex en tu proyecto"),
            ("cortex create-spec", "Crear especificación antes de codear"),
            ("cortex save-session", "Guardar sesión de trabajo al terminar"),
            ("cortex search", "Buscar en tu memoria (episódica + semántica)"),
            ("cortex context", "Inyectar contexto por archivos modificados"),
            ("cortex doctor", "Verificar salud del proyecto"),
            ("cortex stats", "Ver estadísticas de memoria"),
            ("cortex remember", "Almacenar una memoria episódica manual"),
            ("cortex forget", "Eliminar una memoria por ID"),
            ("cortex inject", "Configurar tu IDE para usar Cortex"),
            ("cortex tutor", "Esta guía que estás viendo ahora"),
            ("cortex hint", "Tip contextual: qué hacer ahora"),
        ]
        for cmd, desc in commands:
            table.add_row(cmd, desc)

        footer = "\n[dim]Más comandos: cortex --help  |  Enterprise: cortex tutor → tema 6[/dim]"

        console.print(Panel(table, title="📋 COMANDOS ESENCIALES", border_style="yellow", padding=(1, 1)))
        console.print(footer)
