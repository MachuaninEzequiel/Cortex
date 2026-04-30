"""Tópico: Vault — Tu Base de Conocimiento."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel


class VaultTopic:
    @property
    def title(self) -> str:
        return "Vault y Documentación"

    @property
    def icon(self) -> str:
        return "📁"

    @property
    def one_liner(self) -> str:
        return "Estructura del vault y qué va a Git"

    @property
    def slug(self) -> str:
        return "vault"

    @property
    def guide_path(self) -> str | None:
        return "docs/guides/vault-structure.md"

    def render(self, console: Console) -> None:
        content = (
            "[bold]vault/[/]\n"
            "  ├── [cyan]specs/[/]        → Especificaciones técnicas (pre-trabajo)\n"
            "  ├── [cyan]sessions/[/]     → Notas de sesiones (post-trabajo)\n"
            "  ├── [cyan]decisions/[/]    → Decisiones arquitectónicas\n"
            "  ├── [cyan]runbooks/[/]     → Guías operativas\n"
            "  └── [cyan]hu/[/]           → Work items importados (Jira, etc.)\n"
            "\n"
            "[bold yellow]¿Qué va a Git/Master?[/]\n"
            "  [green]✅[/] vault/          (tu knowledge base versionada)\n"
            "  [green]✅[/] config.yaml     (configuración del proyecto)\n"
            "  [green]✅[/] .cortex/org.yaml (si usás enterprise)\n"
            "  [red]❌[/] .memory/        (base de datos local, en .gitignore)\n"
            "\n"
            "[bold yellow]Comandos clave:[/]\n"
            "  [cyan]cortex sync-vault[/]     → Re-indexar el vault\n"
            "  [cyan]cortex validate-docs[/]  → Validar estructura y frontmatter\n"
            "  [cyan]cortex index-docs[/]     → Indexar docs como memoria semántica\n"
            "\n"
            "📖 Estructura detallada: [link]docs/guides/vault-structure.md[/link]"
        )
        console.print(Panel(content, title="📁 VAULT — Tu Base de Conocimiento", border_style="green", padding=(1, 2)))
