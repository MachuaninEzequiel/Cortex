"""``cortex hu`` — gestión de work items trackeados (import read-only).

Extraído del monolito cli/main.py (deuda V2, Obra 01 fase P4).
"""

from __future__ import annotations

import typer

from cortex.cli.common import _load_memory

hu_app = typer.Typer(help="Tracked work item management (read-only external import).")


@hu_app.command("import")
def hu_import(
    external_id: str = typer.Argument(..., help="External item key, for example PROJ-123."),
    provider: str = typer.Option("jira", "--provider", help="External provider name."),
    no_remember: bool = typer.Option(False, "--no-remember", help="Skip episodic summary storage."),
) -> None:
    """Import one external tracked item into ``vault/hu/``."""
    mem = _load_memory()
    path = mem.import_work_item(external_id, provider=provider, remember=not no_remember)
    typer.echo(f"Tracked item imported -> {path}")


@hu_app.command("list")
def hu_list() -> None:
    """List tracked item notes already stored in ``vault/hu/``."""
    mem = _load_memory()
    notes = mem.list_work_item_notes()
    if not notes:
        typer.echo("No tracked items imported yet.")
        return
    for note in notes:
        typer.echo(str(note))


@hu_app.command("show")
def hu_show(
    item_id: str = typer.Argument(..., help="Tracked item ID, for example PROJ-123."),
) -> None:
    """Show the local vault note path for one tracked item."""
    mem = _load_memory()
    try:
        note = mem.get_work_item_note(item_id)
    except FileNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(str(note))
