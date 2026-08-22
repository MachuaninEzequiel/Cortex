"""``cortex next`` — lista de acciones sugeridas sin TUI (Obra 05 Fase B).

Para agentes y scripts. Gate: <2s en repo mediano (contexto perezoso;
snapshot on-open, no escaneo completo salvo ``--all``).
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from cortex.action_engine.actions import build_default_registry
from cortex.action_engine.context import ActionContext
from cortex.action_engine.scheduler import Scheduler


def register(app) -> None:
    """Registra ``cortex next`` en el app principal."""

    @app.command(name="next")
    def next_action(
        all_: bool = typer.Option(
            False, "--all", help="Escaneo completo (incluye checks costosos)."
        ),
        json_output: bool = typer.Option(
            False, "--json", help="Salida JSON para agentes/scripts."
        ),
        explain: bool = typer.Option(
            False, "--explain-why-not", help="Incluye por qué NO se propone cada acción."
        ),
        stats: bool = typer.Option(
            False, "--stats", help="Métrica del motor: % decisiones automáticas (Fase E)."
        ),
        project_root: str | None = typer.Option(
            None, "--project-root", help="Project root (default: descubrir desde cwd)."
        ),
    ) -> None:
        """¿Qué hago ahora con Cortex? Acciones priorizadas, sin TUI."""
        import time

        t0 = time.perf_counter()
        try:
            ctx = ActionContext.from_project_root(
                Path(project_root).resolve() if project_root else None
            )
        except FileNotFoundError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1) from exc

        if not ctx.config_existe():
            typer.echo(
                f"Cortex no está configurado en {ctx.layout.workspace_root} "
                "(no encuentro config.yaml) — corré `cortex setup agent` primero.",
                err=True,
            )
            raise typer.Exit(1)

        if stats:
            from cortex.action_engine.metrics import calcular_metricas
            from cortex.action_engine.store import ActionLog

            metricas = calcular_metricas(ActionLog(ctx.dot_cortex))
            typer.echo(
                json.dumps(
                    {
                        "total_ejecuciones": metricas.total_ejecuciones,
                        "via_auto": metricas.via_auto,
                        "via_usuario": metricas.via_usuario,
                        "pct_motor": metricas.pct_motor,
                        "dias_con_interaccion": len(metricas.dias_con_interaccion),
                        "por_accion": metricas.acciones_por_id,
                        "definicion": (
                            "pct_motor alto + volumen estable = el motor toma "
                            "las decisiones rutinarias (target dueño: abrir el "
                            "menú <1 vez/día activo)"
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return

        registry = build_default_registry(ctx)
        scheduler = Scheduler(preferences=__import__(
            "cortex.action_engine.store", fromlist=["PreferencesStore"]
        ).PreferencesStore(ctx.dot_cortex))

        propuestas = scheduler.propose(registry, deep=all_)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        if json_output:
            payload = {
                "elapsed_ms": elapsed_ms,
                "acciones": [
                    {
                        "id": p.action.id,
                        "title": p.action.title,
                        "category": p.action.category,
                        "effect": p.action.effect,
                        "cost": p.action.cost,
                        "reversible": p.action.reversible,
                        "auto_ok": p.action.auto_ok,
                        "score": p.score,
                    }
                    for p in propuestas
                ],
            }
            if explain:
                payload["why_not"] = scheduler.explain_why_not(registry)
            typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        if not propuestas:
            typer.echo("✅ Nada pendiente — tu workspace está al día.")
            if explain:
                for aid, razones in scheduler.explain_why_not(registry).items():
                    typer.echo(f"  · {aid}: {'; '.join(razones)}")
            return

        typer.echo(f"🧠 Cortex · {len(propuestas)} acción(es) sugeridas:\n")
        for i, p in enumerate(propuestas, 1):
            auto = " [auto-ok]" if p.action.auto_ok else ""
            typer.echo(f" [{i}] {p.action.title}")
            typer.echo(f"     id: {p.action.id} · costo: {p.action.cost}{auto} · score: {p.score}")
            typer.echo(f"     efecto: {p.action.effect}\n")

        if explain:
            typer.echo("— No propuestas —")
            for aid, razones in scheduler.explain_why_not(registry).items():
                typer.echo(f"  · {aid}: {'; '.join(razones)}")

        typer.echo(
            f"\n[dim]{elapsed_ms}ms · ejecutá `cortex next --json` para salida machine-readable[/dim]"
        )
