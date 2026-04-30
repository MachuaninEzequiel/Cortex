"""Tópico: Pipeline CI/CD — DevSecDocOps."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel


class PipelineTopic:
    @property
    def title(self) -> str:
        return "Pipeline CI/CD"

    @property
    def icon(self) -> str:
        return "⚙️"

    @property
    def one_liner(self) -> str:
        return "Cómo funciona el pipeline y cómo cambiar módulos"

    @property
    def slug(self) -> str:
        return "pipeline"

    @property
    def guide_path(self) -> str | None:
        return "docs/guides/pipeline-setup.md"

    def render(self, console: Console) -> None:
        content = (
            "Cortex ejecuta [bold]4 stages[/] en orden:\n"
            "  [cyan]Security[/] → [cyan]Lint[/] → [cyan]Test[/] → [cyan]Documentation[/]\n"
            "\n"
            "Cada stage se configura en [bold]config.yaml[/]:\n"
            "  [dim]pipeline.stages.security.enabled: true/false[/]\n"
            "  [dim]pipeline.stages.security.block_on_failure: true/false[/]\n"
            "\n"
            "[bold yellow]Módulos intercambiables:[/]\n"
            "  Security: npm audit (default) o tu propio script\n"
            "  Lint:     ruff (default) o eslint, pylint, flake8...\n"
            "  Test:     pytest (default) o jest, vitest, go test...\n"
            "  Docs:     cortex verify-docs (default)\n"
            "\n"
            "[bold yellow]Modos de enforcement:[/]\n"
            "  [green]block_on_failure: false[/] → Advisory (advierte, no bloquea)\n"
            "  [red]block_on_failure: true[/]  → Enforced (bloquea el merge)\n"
            "\n"
            "Setup rápido: [cyan]cortex setup pipeline[/]\n"
            "\n"
            "📖 Setup completo: [link]docs/guides/pipeline-setup.md[/link]\n"
            "📖 Módulos custom: [link]docs/guides/pipeline-custom-modules.md[/link]"
        )
        console.print(Panel(content, title="⚙️  PIPELINE CI/CD — DevSecDocOps", border_style="red", padding=(1, 2)))
