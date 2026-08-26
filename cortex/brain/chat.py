"""DEPRECATED (2026-08-25, doc 12 §4.2): ver cortex/brain/__init__.py.

Loop de chat del brain (BRAIN-1, sin LLM).

``ChatSession`` es inyectable (input_fn/console) para testear sin TTY y
sin modelo. BRAIN-2 agrega el backend llama.cpp ENCIMA de este loop vía
el mismo ``route_intent`` + tool-calling.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from cortex.action_engine.context import ActionContext
from cortex.brain.router import route_intent
from cortex.brain.tools import Tier, build_tools

_BANNER = """\
   ______ __  __ ____  _____ _   _____  __
  / ____// / / //  _// ___// | / /   \\/ /
 / /    / /_/ / / /  \\__ \\/  |/ / /\\ / /
/ /___ / __  _/ / / ___/ / /|  / /_/  /
\\____//_/ /_/___//____/_/ |_/\\____/
"""


@dataclass
class BrainSession:
    project_root: Path | None = None
    input_fn: object = input
    console_obj: Console | None = None

    def __post_init__(self) -> None:
        self.console = self.console_obj or Console()
        self.ctx: ActionContext | None = None
        self.tools = {}

    # ── arranque ────────────────────────────────────────────────────

    def abrir(self) -> bool:
        """Descubre el proyecto; False si no está inicializado."""
        try:
            self.ctx = ActionContext.from_project_root(self.project_root)
        except FileNotFoundError as exc:
            self.console.print(f"[red]{exc}[/red]")
            self.console.print("[dim]Corré `cortex init` primero.[/dim]")
            return False
        self.tools = build_tools(self.ctx)
        return True

    def banner(self) -> None:
        proyecto = self.ctx.layout.repo_root.name if self.ctx else "?"
        modo = "determinista (--no-model) · BRAIN-1"
        self.console.print(
            Panel(
                f"[bold cyan]{_BANNER}[/bold cyan]\n"
                f"[dim]Experto de [b]{proyecto}[/b] · {modo}\n"
                f"Preguntame sobre este repo o usá /help.[/dim]",
                border_style="magenta",
                title="🧠 CORTEX BRAIN",
            )
        )

    def help_texto(self) -> str:
        lineas = ["Comandos:"]
        for nombre, spec in sorted(self.tools.items()):
            lineas.append(f"  · {nombre} {spec.args_hint} — {spec.description} "
                          f"[dim]({spec.tier.value})[/dim]")
        lineas.append("  · /quit — salir")
        lineas.append("[dim]Modo estricto: propongo mutaciones con su comando "
                      "CLI; jamás las ejecuto.[/dim]")
        return "\n".join(lineas)

    # ── despacho ────────────────────────────────────────────────────

    def dispatch(self, texto: str) -> str:
        """Procesa una entrada y devuelve la respuesta (puro → testeable)."""
        intent = route_intent(texto)

        if intent.slash == "quit":
            raise SystemExit(0)
        if intent.slash == "help":
            return self.help_texto()
        if intent.slash:
            intent.tool = {
                "doctor": "cortex.health",
                "stats": "vault.stats",
                "session": "session.current",
                "webgraph": "webgraph.serve",
                "actions": "actions.propose",
                "search": "memory.search",
            }.get(intent.slash)
            if intent.tool is None:
                return f"Slash sin herramienta asociada: /{intent.slash}"
            intent.args.setdefault(
                "query", intent.args.get("resto", "")
            ) if intent.slash == "search" else None

        if intent.tool is None:
            return (
                "No entendí eso. Sé responder sobre ESTE repo: estado/salud, "
                "búsquedas en memoria, docs relacionados, stats del vault, "
                "sesión activa, webgraph y acciones pendientes.\n" + self.help_texto()
            )

        spec = self.tools[intent.tool]
        try:
            resultado = spec.handler(**intent.args)
        except FileNotFoundError as exc:
            return (
                f"⚠ No puedo ejecutar {intent.tool}: el proyecto no está "
                f"inicializado.\n{exc}\nCorré `cortex init` y volvé a intentar."
            )
        except Exception as exc:  # noqa: BLE001 — herramienta fallida ≠ chat roto
            return f"⚠ {intent.tool} falló: {exc}"
        prefijo = "" if spec.tier is Tier.READ else "🔧 [safe-action] "
        return f"{prefijo}{resultado}"


def run_brain(project_root: Path | None = None, *, max_loops: int = 200) -> None:
    """Entry point del comando `cortex brain`."""
    sesion = BrainSession(project_root=project_root)
    if not sesion.abrir():
        sys.exit(1)
    sesion.banner()
    for _ in range(max_loops):
        try:
            texto = input("brain › ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not texto:
            continue
        try:
            sesion.console.print(sesion.dispatch(texto))
        except SystemExit:
            console_out = "👋 Hasta la próxima."
            sesion.console.print(console_out)
            break
        except Exception as exc:  # noqa: BLE001 — el brain nunca revienta
            sesion.console.print(f"[red]Error interno:[/red] {exc}")
