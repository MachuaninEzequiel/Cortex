"""Tópico: Integración IDE — Model Context Protocol."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel


class IDEIntegrationTopic:
    @property
    def title(self) -> str:
        return "Integración IDE"

    @property
    def icon(self) -> str:
        return "🔌"

    @property
    def one_liner(self) -> str:
        return "Cómo conectar Cortex con tu IDE via MCP"

    @property
    def slug(self) -> str:
        return "ide"

    @property
    def guide_path(self) -> str | None:
        return None

    def render(self, console: Console) -> None:
        content = (
            "Cortex se conecta a tu IDE via [bold]MCP Server[/].\n"
            "\n"
            "[bold yellow]IDEs soportados:[/]\n"
            "  ⭐ [bold cyan]Pi Coding Agent[/]  (recomendado)\n"
            "  • Cursor  • VSCode (Cline/Roo)  • Claude Code\n"
            "  • Claude Desktop  • Windsurf  • Zed  • Antigravity\n"
            "\n"
            "[bold yellow]Setup rápido:[/]\n"
            "  [cyan]cortex inject --ide cursor[/]        → Cursor\n"
            "  [cyan]cortex inject --ide claude-code[/]   → Claude Code\n"
            "  [cyan]cortex inject[/]                     → Menú interactivo\n"
            "\n"
            "[bold yellow]¿Qué hace inject?[/]\n"
            "  • Configura el servidor MCP en tu IDE\n"
            "  • Inyecta perfiles de agente Cortex\n"
            "  • Hace [green]merge seguro[/] (no sobreescribe tu config)\n"
            "  • Crea backup automático antes de modificar\n"
            "\n"
            "[dim]Manual: cortex mcp-server --project-root /ruta/al/proyecto[/]\n"
            "\n"
            "📖 Configuración detallada: ver README.md sección MCP"
        )
        console.print(Panel(content, title="🔌 INTEGRACIÓN IDE — Model Context Protocol", border_style="cyan", padding=(1, 2)))
