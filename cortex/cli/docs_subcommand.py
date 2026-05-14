"""cortex.cli.docs_subcommand - ``cortex docs`` subcommand group.

In Fase 02 this group exposes a single command, ``routing-table``, which
inspects the canonical routing table. Later phases add ``validate``,
``migrate``, ``vectorization``, ``schema``, ``scaffold``, etc.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Optional

import typer

from cortex.documentation.doc_type import DocType
from cortex.documentation.errors import UnknownDocTypeError
from cortex.documentation.routing import list_all_routes, resolve_route

app = typer.Typer(help="Canonical documentation system commands.")

# Vector cache operations live under ``cortex docs vectorization`` (Fase 06).
from cortex.cli.docs_vectorization import app as _vec_app
app.add_typer(_vec_app, name="vectorization")

# Migration / validate / restore (Fase 11).
from cortex.cli.docs_migrate import (
    list_backups_cmd as _list_backups_cmd,
    migrate as _migrate_cmd,
    restore as _restore_cmd,
    validate as _validate_cmd,
)
app.command(name="migrate")(_migrate_cmd)
app.command(name="validate")(_validate_cmd)
app.command(name="restore")(_restore_cmd)
app.command(name="list-backups")(_list_backups_cmd)

# Structural search with EnrichmentFilters (Fase 13 backlog).
from cortex.cli.docs_search import search as _search_cmd
app.command(name="search")(_search_cmd)


@app.callback()
def _docs_main() -> None:
    """Canonical documentation system commands.

    Subcommands:
        routing-table    Print the canonical DOC_TYPE_ROUTING table.
        vectorization    Inspect and manage the persistent vector cache.
    """
    # Forces Typer to treat ``app`` as a command group even when it only has
    # one subcommand. Future phases add ``validate``, ``migrate``, etc.


def _spec_to_serializable(spec) -> dict:
    """Convert a RouteSpec to a JSON-friendly dict."""
    raw = asdict(spec)
    # Enum -> str.
    raw["doc_type"] = spec.doc_type.value
    # Path -> str.
    raw["template_path"] = str(spec.template_path)
    # writer Callable -> name or None.
    if spec.writer is None:
        raw["writer"] = None
    else:
        raw["writer"] = getattr(spec.writer, "__name__", repr(spec.writer))
    return raw


@app.command("routing-table")
def routing_table(
    doc_type: Optional[str] = typer.Option(
        None, "--doc-type", help="Filter by DocType slug (e.g. 'adr')."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output as JSON."
    ),
) -> None:
    """Print the canonical DOC_TYPE_ROUTING table."""
    if doc_type is not None:
        try:
            dt = DocType(doc_type)
        except ValueError as exc:
            raise typer.BadParameter(
                f"Unknown doc_type: {doc_type!r}. "
                f"Valid: {[d.value for d in DocType]}"
            ) from exc
        try:
            spec = resolve_route(dt)
        except UnknownDocTypeError as exc:
            raise typer.Exit(code=1) from exc
        specs = [spec]
    else:
        specs = list_all_routes()

    if json_output:
        payload = [_spec_to_serializable(s) for s in specs]
        if len(payload) == 1 and doc_type is not None:
            typer.echo(json.dumps(payload[0], indent=2))
        else:
            typer.echo(json.dumps(payload, indent=2))
        return

    # Human-readable table.
    header = (
        f"{'DocType':<14} {'Subfolder':<14} {'Filename pattern':<38} "
        f"{'Writer':<22} {'Indexer':<8} {'Promote':<14}"
    )
    typer.echo(header)
    typer.echo("-" * len(header))
    for spec in specs:
        writer_name = (
            getattr(spec.writer, "__name__", repr(spec.writer))
            if spec.writer is not None
            else "(pending)"
        )
        if spec.promotable:
            promote = spec.promotion_mode
        else:
            promote = "no"
        typer.echo(
            f"{spec.doc_type.value:<14} {spec.subfolder:<14} "
            f"{spec.filename_template:<38} {writer_name:<22} "
            f"{spec.indexer:<8} {promote:<14}"
        )
