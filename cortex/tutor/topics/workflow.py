"""Tópico: Flujo de Trabajo — Modelo Tripartito."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel


class WorkflowTopic:
    @property
    def title(self) -> str:
        return "Flujo de Trabajo"

    @property
    def icon(self) -> str:
        return "🔄"

    @property
    def one_liner(self) -> str:
        return "El modelo tripartito: sync → SDDwork → documenter"

    @property
    def slug(self) -> str:
        return "workflow"

    @property
    def guide_path(self) -> str | None:
        return "docs/enterprise/MANIFIESTO-CORTEX-ENTERPRISE.md"

    def render(self, console: Console) -> None:
        content = (
            "[bold green]FASE 1 →[/] [bold]cortex-sync[/] (El Analista)\n"
            "  Recupera contexto histórico y crea una especificación técnica.\n"
            "  Comando: [cyan]cortex create-spec[/]\n"
            "\n"
            "[bold yellow]FASE 2 →[/] [bold]cortex-SDDwork[/] (El Orquestador)\n"
            "  Implementa con Intelligent Routing:\n"
            "  [green]Fast Track 🟢[/] Tareas simples → edita directo + valida.\n"
            "  [red]Deep Track 🔴[/] Tareas complejas → delega a subagentes.\n"
            "    Explorer → Implementer → Security → Test\n"
            "\n"
            "[bold magenta]FASE 3 →[/] [bold]cortex-documenter[/] (El Guardián)\n"
            "  Persiste decisiones, cambios y TODOs en el vault.\n"
            "  Comando: [cyan]cortex save-session[/]\n"
            "\n"
            "[dim]Ninguna tarea se considera terminada sin la Fase 3.[/]\n"
            "\n"
            "📖 Detalle completo: [link]docs/enterprise/MANIFIESTO-CORTEX-ENTERPRISE.md[/link]"
        )
        console.print(Panel(content, title="🔄 FLUJO DE TRABAJO — Modelo Tripartito", border_style="blue", padding=(1, 2)))
