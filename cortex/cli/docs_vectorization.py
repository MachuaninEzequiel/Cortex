"""cortex.cli.docs_vectorization - ``cortex docs vectorization`` subcommands.

Inspects, compacts and clears the vector cache introduced in Fase 06 of the
canonical-documentation initiative.
"""

from __future__ import annotations

import json as _json
from pathlib import Path

import typer

from cortex.semantic.vector_cache import VectorCache
from cortex.workspace.layout import WorkspaceLayout

app = typer.Typer(help="Vector cache operations.")


@app.callback()
def _vec_main() -> None:
    """Vector cache operations.

    Subcommands:
        stats     Print cache statistics.
        compact   Reclaim space from invalidated entries.
        clear     Remove all cached vectors.
    """


def _resolve_cache(project_root: str | None) -> VectorCache:
    root = Path(project_root).expanduser().resolve() if project_root else Path.cwd().resolve()
    layout = WorkspaceLayout.discover(root)
    cache_dir = Path(layout.workspace_root) / ".cortex" / "vectors"
    return VectorCache(cache_dir)


@app.command()
def stats(
    project_root: str | None = typer.Option(
        None, "--project-root", help="Project root where config.yaml lives.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Print vector cache statistics."""
    cache = _resolve_cache(project_root)
    s = cache.stats()
    payload = {
        "cache_dir": str(cache.cache_dir),
        "total_entries": s.total_entries,
        "valid_entries": s.valid_entries,
        "invalidated_entries": s.invalidated_entries,
        "size_bytes": s.size_bytes,
        "hit_count": s.hit_count,
        "miss_count": s.miss_count,
        "hit_rate": s.hit_rate,
    }
    if json_output:
        typer.echo(_json.dumps(payload, indent=2))
        return
    typer.echo(f"Cache dir: {payload['cache_dir']}")
    typer.echo(f"Total entries: {payload['total_entries']}")
    typer.echo(f"Valid: {payload['valid_entries']}")
    typer.echo(f"Invalidated: {payload['invalidated_entries']}")
    typer.echo(f"Size: {payload['size_bytes'] / 1024:.1f} KB")
    typer.echo(f"Hit rate: {payload['hit_rate'] * 100:.1f}%")


@app.command()
def compact(
    project_root: str | None = typer.Option(
        None, "--project-root", help="Project root where config.yaml lives.",
    ),
) -> None:
    """Reclaim space from invalidated entries (rewrites chunks.bin)."""
    cache = _resolve_cache(project_root)
    before = cache.stats()
    cache.compact()
    after = cache.stats()
    typer.echo(
        f"Compacted: {before.size_bytes / 1024:.1f}KB "
        f"-> {after.size_bytes / 1024:.1f}KB "
        f"(reclaimed {(before.size_bytes - after.size_bytes) / 1024:.1f}KB)"
    )


@app.command()
def clear(
    project_root: str | None = typer.Option(
        None, "--project-root", help="Project root where config.yaml lives.",
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Skip confirmation prompt.",
    ),
) -> None:
    """Delete every cached vector. The cache rebuilds on the next sync."""
    cache = _resolve_cache(project_root)
    s = cache.stats()
    if not yes and s.total_entries > 0:
        typer.echo(
            f"About to clear {s.total_entries} cached vectors "
            f"({s.size_bytes / 1024:.1f}KB)."
        )
        typer.confirm("Proceed?", abort=True)
    cache.clear()
    typer.echo("Cache cleared.")
