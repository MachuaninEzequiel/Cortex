"""Comando `cortex brain` — asistente local experto del proyecto."""

from __future__ import annotations

from pathlib import Path

import typer


def register(app) -> None:
    """Registra ``cortex brain`` (nivel-0)."""

    @app.command(name="brain")
    def brain(
        project_root: Path | None = typer.Option(
            None, "--project-root", help="Project root (default: descubrir desde cwd)."
        ),
        no_model: bool = typer.Option(
            True, "--no-model/--model",
            help="BRAIN-1: solo router determinista. --model llega en BRAIN-2 (llama.cpp).",
        ),
    ) -> None:
        """🧠 Asistente local experto de ESTE proyecto (solo lectura + safe-actions)."""
        from cortex.brain.chat import run_brain

        if not no_model:
            # BRAIN-1: el backend LLM (llama.cpp/GGUF, nativo en Rust) todavía
            # no existe; el flag --model se honra avisando y degradando.
            typer.echo(
                "--model: backend LLM aún no disponible (BRAIN-2 nativo en Rust "
                "pendiente). Se usa el router determinista."
            )
        run_brain(
            Path(project_root).resolve() if project_root else None,
        )
