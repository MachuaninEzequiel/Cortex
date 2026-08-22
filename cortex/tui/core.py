"""Núcleo de la TUI Home (Obra 05 Fase D, plan §4.2/§4.3).

- ``snapshot_home``: snapshot barato <300ms (mtimes + puntero activo +
  conteos; SIN abrir ChromaDB salvo demanda).
- ``render_home`` / ``render_actions_screen``: renderers puros testeables.
- ``run_home``: loop de teclas de una letra (a/s/…/q). La TUI orquesta
  comandos y servicios existentes — nunca duplica lógica.
"""

from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cortex.action_engine.context import ActionContext
from cortex.action_engine.i18n import DEFAULT_LANG, etiquetas, idioma_de
from cortex.action_engine.learning import Learner
from cortex.action_engine.models import ProposedAction
from cortex.action_engine.runner import Runner
from cortex.action_engine.scheduler import Scheduler
from cortex.action_engine.store import PreferencesStore

MAX_ACCIONES = 5


@dataclass(frozen=True)
class HomeState:
    proyecto: str
    rama: str | None
    sesion_line: str | None
    acciones: tuple[ProposedAction, ...]
    vault_notas: int
    vault_sin_validar: int | None
    doctor_items: tuple[tuple[str, str], ...]
    elapsed_ms: int = 0
    errores: tuple[str, ...] = field(default=())
    idioma: str = "es"


# ── snapshot ───────────────────────────────────────────────────────────────


def _rama_actual(repo_root: Path) -> str | None:
    git = repo_root / ".git"
    if not git.exists():
        return None
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root,
            capture_output=True, text=True, timeout=5,
        )
        return proc.stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


def _sesion_activa_line(ctx: ActionContext) -> str | None:
    try:
        abiertas = [r for r in ctx.sessions.list() if r.status.value == "open"]
    except Exception:  # noqa: BLE001
        return None
    if not abiertas:
        return None
    r = abiertas[0]
    return f"{r.session_id} · OPEN · {len(r.checkpoints)} checkpoints"


def snapshot_home(project_root: Path | None = None) -> HomeState:
    """Snapshot barato del estado para el Home (gate <300ms)."""
    t0 = time.perf_counter()
    errores: list[str] = []
    try:
        ctx = ActionContext.from_project_root(project_root)
    except FileNotFoundError as exc:
        return HomeState(
            proyecto=str(exc)[:60], rama=None, sesion_line=None,
            acciones=(), vault_notas=0, vault_sin_validar=None,
            doctor_items=(("init", "pendiente"),),
            elapsed_ms=int((time.perf_counter() - t0) * 1000),
            errores=(str(exc),),
            idioma=DEFAULT_LANG,
        )

    root = ctx.layout.workspace_root.parent  # repo root para rama/doctor-lite
    vault = ctx.vault_path
    notas = len(list(vault.rglob("*.md"))) if vault.exists() else 0

    config_ok = ctx.config_existe()
    doctor_items: list[tuple[str, str]] = [
        ("config", "✓" if config_ok else "✗"),
        ("git", "✓" if (root / ".git").exists() else "—"),
    ]
    if not config_ok:
        doctor_items.append(("init", "pendiente — corré `cortex init`"))

    try:
        registry = __import__(
            "cortex.action_engine.actions", fromlist=["build_default_registry"]
        ).build_default_registry(ctx)
        from cortex.action_engine.signals import leer_senales

        sched = Scheduler(
            preferences=PreferencesStore(ctx.dot_cortex),
            senales=leer_senales(ctx.dot_cortex),
        )
        propuestas = sched.propose(registry)
    except Exception as exc:  # noqa: BLE001 — el home nunca revienta
        propuestas = []
        errores.append(f"action engine: {exc}")

    idioma = idioma_de(ctx.layout.config_path)
    state = HomeState(
        proyecto=root.name,
        rama=_rama_actual(root),
        sesion_line=_sesion_activa_line(ctx),
        acciones=tuple(propuestas[:MAX_ACCIONES]),
        vault_notas=notas,
        vault_sin_validar=None,
        doctor_items=tuple(doctor_items),
        errores=tuple(errores),
        idioma=idioma,
    )
    # dataclass frozen → reconstruir con elapsed real
    return HomeState(
        proyecto=state.proyecto, rama=state.rama,
        sesion_line=state.sesion_line, acciones=state.acciones,
        vault_notas=state.vault_notas, vault_sin_validar=state.vault_sin_validar,
        doctor_items=state.doctor_items,
        elapsed_ms=int((time.perf_counter() - t0) * 1000),
        errores=state.errores,
        idioma=state.idioma,
    )


# ── renderers puros ────────────────────────────────────────────────────────


def render_home(state: HomeState) -> Panel:
    et = etiquetas(state.idioma)
    tabla = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    tabla.add_column("k", style="bold cyan", width=11)
    tabla.add_column("v")

    tabla.add_row(et["sesion"], state.sesion_line or et["ninguna"])
    n_acc = len(state.acciones)
    tabla.add_row(
        et["pendiente"],
        f"{n_acc} {et['acciones_sugeridas']}" if n_acc else et["sin_pendiente"],
    )
    tabla.add_row(et["vault"], f"{state.vault_notas} {et['notas']}")
    doctor = "  ".join(f"{k}: {v}" for k, v in state.doctor_items)
    tabla.add_row(et["salud"], doctor)
    if state.errores:
        tabla.add_row("AVISO", "; ".join(state.errores))

    titulo = f"Cortex · {state.proyecto}"
    if state.rama:
        titulo += f" · rama: {state.rama}"
    return Panel(
        tabla,
        title=titulo,
        subtitle=(
            "[dim]a=acciones  s=sesión  /=buscar  t=tutor  d=doctor  q=salir"
            f"  · snapshot {state.elapsed_ms}ms[/dim]"
        ),
        border_style="cyan",
    )


def render_actions_screen(proposals: list[ProposedAction]) -> Panel:
    tabla = Table(show_header=True, box=None, padding=(0, 1), expand=True)
    tabla.add_column("#", style="bold yellow", width=3)
    tabla.add_column("acción")
    tabla.add_column("costo", width=8)
    tabla.add_column("seguridad", width=12)

    for i, p in enumerate(proposals, 1):
        a = p.action
        seguridad = (
            "auto-ok"
            if a.auto_ok
            else ("reversible" if a.reversible else "⚠ irreversible")
        )
        tabla.add_row(f"[{i}]", f"{a.title}\n[dim]{a.effect}[/dim]", a.cost, seguridad)

    return Panel(
        tabla,
        title="Acciones sugeridas / Suggested actions",

        subtitle=(
            "[dim]a=ejecutar todas las auto-ok · N=elegir · "
            "s=saltar la elegida · n=nunca más · q=volver[/dim]"
        ),
        border_style="magenta",
    )


# ── loop interactivo ───────────────────────────────────────────────────────


def _ejecutar_accion(ctx: ActionContext, proposal: ProposedAction, *, approved: bool, via: str = "user") -> None:
    runner = Runner(directory=ctx.dot_cortex)
    resultado = runner.execute(proposal.action, approved=approved, via=via)
    console = Console()
    icono = "✅" if resultado.ok else "❌"
    console.print(f"{icono} [{proposal.action.id}] {resultado.message}")


def _pantalla_acciones(ctx: ActionContext, console: Console) -> None:
    registry = __import__(
        "cortex.action_engine.actions", fromlist=["build_default_registry"]
    ).build_default_registry(ctx)
    prefs = PreferencesStore(ctx.dot_cortex)
    learner = Learner(prefs)
    sched = Scheduler(preferences=prefs)
    proposals = sched.propose(registry)
    if not proposals:
        console.print("[green]✅ Sin acciones pendientes.[/green]")
        return

    console.print(render_actions_screen(proposals))
    eleccion = input("Elegí (a/Número/q): ").strip().lower()
    if eleccion == "q" or not eleccion:
        return

    if eleccion == "a":
        for p in proposals:
            if p.action.auto_ok:
                learner.registrar_decision(p.action.id, "accept")
                _ejecutar_accion(ctx, p, approved=False, via="auto")
        return

    if eleccion.isdigit() and 1 <= int(eleccion) <= len(proposals):
        propuesta = proposals[int(eleccion) - 1]
        sub = input("[e]jecutar / [s]altar / [n]unca más: ").strip().lower()
        if sub == "e":
            learner.registrar_decision(propuesta.action.id, "accept")
            _ejecutar_accion(ctx, propuesta, approved=True)
        elif sub == "s":
            learner.registrar_decision(propuesta.action.id, "skip")
            console.print(f"[dim]salteada: {propuesta.action.id}[/dim]")
        elif sub == "n":
            learner.registrar_decision(propuesta.action.id, "never")
            console.print(f"[dim]nunca más: {propuesta.action.id}[/dim]")


def _pantalla_busqueda(ctx: ActionContext, console: Console) -> None:
    query = input("Query: ").strip()
    if not query:
        return
    result = ctx.mem.retrieve(query, top_k=8)
    if not result.unified_hits:
        console.print("[dim]sin resultados[/dim]")
        return
    tabla = Table(show_header=True, box=None, padding=(0, 1))
    tabla.add_column("#", width=3)
    tabla.add_column("fuente", width=9)
    tabla.add_column("score", width=8)
    tabla.add_column("título")
    for i, hit in enumerate(result.unified_hits, 1):
        tabla.add_row(str(i), hit.source, f"{hit.score:.4f}", hit.display_title)
    console.print(tabla)

    eleccion = input("Nº para marcar útil (enter = nada): ").strip()
    if eleccion.isdigit() and 1 <= int(eleccion) <= len(result.unified_hits):
        hit = result.unified_hits[int(eleccion) - 1]
        memory_id = getattr(hit.entry, "id", None)
        if memory_id:
            from cortex.feedback_loop import ExplicitFeedback, FeedbackCollector
            from cortex.feedback_store import FeedbackStore

            collector = FeedbackCollector(store=FeedbackStore(ctx.dot_cortex))
            collector.add_feedback(
                memory_id,
                ExplicitFeedback(source="tui", feedback_type="positive"),
            )
            console.print(f"[dim]marcado útil: {memory_id}[/dim]")


def run_home(project_root: Path | None = None, *, max_loops: int = 50) -> None:
    """Loop principal del Home (`cortex` sin argumentos)."""
    console = Console()
    for _ in range(max_loops):  # cota defensiva para tests/CI
        state = snapshot_home(project_root)
        console.clear()
        console.print(render_home(state))

        try:
            tecla = input("Opción: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            console.print()
            return
        if tecla in ("q", "quit", "exit", ""):
            return
        try:
            ctx = ActionContext.from_project_root(project_root)
        except FileNotFoundError:
            console.print("[red]Proyecto sin inicializar — corré `cortex init`.[/red]")
            return

        if tecla == "a":
            _pantalla_acciones(ctx, console)
        elif tecla == "s":
            subprocess.run(
                [sys.executable, "-m", "cortex.cli.main", "session", "watch"],
                cwd=str(Path.cwd()),
            )
        elif tecla == "/":
            _pantalla_busqueda(ctx, console)
        elif tecla == "t":
            from cortex.tutor.engine import TutorEngine

            TutorEngine.default().run()
        elif tecla == "d":
            subprocess.run(
                [sys.executable, "-m", "cortex.cli.main", "doctor"],
                cwd=str(Path.cwd()),
            )
