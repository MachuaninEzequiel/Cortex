"""
cortex.cli._setup_helpers
-------------------------
Helpers compartidos por los comandos ``cortex setup *``.

Fase 6 del plan multi-IDE & MCP hardening (2026-05-15):
Centraliza la seleccion de IDE para que ``cortex setup full`` y
``cortex setup agent`` compartan la misma logica. Antes, ``setup_agent``
tenia un bloque interactivo de ~20 lineas y ``setup_full`` no tenia
prompt en absoluto — obligando al adopter a correr dos comandos para
configurar IDE + pipeline + webgraph.
"""
from __future__ import annotations

import typer

import cortex.ide as cortex_ide


def select_ide_interactive(provided_ide: str | None, non_interactive: bool) -> str | None:
    """Resolve the target IDE for setup.

    Resolution order (orden de precedencia explicito):

    1. Si el usuario paso ``--ide <name>`` (``provided_ide`` no None):
       devolver ese valor sin promptear. CI-friendly y idempotente.
    2. Si ``non_interactive`` esta activo: devolver None (sin IDE).
       NO se prompt-ea — los scripts/CI deben pasar ``--ide`` explicito
       si quieren un IDE configurado.
    3. Default (modo interactivo): mostrar menu numerado de IDEs
       soportados y pedir input.

    Args:
        provided_ide:    Valor de ``--ide`` desde la CLI (None si no se paso).
        non_interactive: True si el usuario paso ``--non-interactive``.

    Returns:
        Nombre del IDE elegido (str), o ``None`` si se decidio omitir
        la configuracion del IDE.
    """
    if provided_ide is not None:
        return provided_ide
    if non_interactive:
        return None

    typer.echo("\nSelect IDE to configure:")
    supported = cortex_ide.get_supported_ides()
    for i, ide_name in enumerate(supported, 1):
        typer.echo(f"  {i}. {ide_name}")
    typer.echo("  0. Skip IDE configuration")

    choice = typer.prompt("\nEnter IDE number or name", default="0")

    if choice == "0":
        return None
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(supported):
            return supported[idx]
        typer.echo("Invalid selection, skipping IDE configuration.")
        return None
    if choice in supported:
        return choice
    typer.echo("Invalid selection, skipping IDE configuration.")
    return None
