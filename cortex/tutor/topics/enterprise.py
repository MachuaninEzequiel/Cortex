"""Tópico: Enterprise Memory — Memoria Corporativa."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel


class EnterpriseTopic:
    @property
    def title(self) -> str:
        return "Enterprise Memory"

    @property
    def icon(self) -> str:
        return "🏢"

    @property
    def one_liner(self) -> str:
        return "Memoria corporativa, promoción y topologías"

    @property
    def slug(self) -> str:
        return "enterprise"

    @property
    def guide_path(self) -> str | None:
        return "docs/guides/enterprise-vault.md"

    def render(self, console: Console) -> None:
        content = (
            "[bold yellow]Modelo de 2 niveles:[/]\n"
            "  [cyan]vault/[/]             → Conocimiento [bold]LOCAL[/] del proyecto\n"
            "  [cyan]vault-enterprise/[/]  → Conocimiento [bold]CORPORATIVO[/] compartido\n"
            "\n"
            "[bold yellow]Flujo de promoción:[/]\n"
            "  Local spec → [dim]candidate[/] → [dim]review[/] → [green]promote[/] → enterprise vault\n"
            "\n"
            "[bold yellow]Topologías disponibles:[/]\n"
            "  • [cyan]small-company[/]         → Equipo chico, vault compartido\n"
            "  • [cyan]multi-project-team[/]    → Varios proyectos, retrieval cruzado\n"
            "  • [cyan]regulated-organization[/] → Review obligatorio, CI enforced\n"
            "  • [cyan]custom[/]                → Config manual completa\n"
            "\n"
            "[bold yellow]Comandos clave:[/]\n"
            "  [cyan]cortex setup enterprise[/]    → Configurar topología\n"
            "  [cyan]cortex promote-knowledge[/]   → Promover docs (--dry-run/--apply)\n"
            "  [cyan]cortex review-knowledge[/]    → Aprobar/rechazar candidatos\n"
            "  [cyan]cortex memory-report[/]       → Ver salud de memoria\n"
            "\n"
            "📖 Guía enterprise: [link]docs/guides/enterprise-vault.md[/link]"
        )
        console.print(Panel(content, title="🏢 ENTERPRISE MEMORY — Memoria Corporativa", border_style="magenta", padding=(1, 2)))
