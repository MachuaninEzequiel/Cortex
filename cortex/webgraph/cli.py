from __future__ import annotations

from pathlib import Path

import typer

from cortex.webgraph.service import WebGraphService

app = typer.Typer(help="Hybrid memory graph commands for Cortex.")


@app.command("export")
def export_snapshot(
    mode: str = typer.Option("hybrid", help="Graph mode: semantic, episodic, hybrid."),
    output: str = typer.Option(None, help="Output path for the JSON snapshot."),
    no_cache: bool = typer.Option(False, "--no-cache", help="Force snapshot rebuild."),
) -> None:
    service = WebGraphService(Path.cwd())
    path = service.export_snapshot(
        output_path=Path(output) if output else None,
        mode=mode,  # type: ignore[arg-type]
        use_cache=not no_cache,
    )
    typer.echo(f"Webgraph snapshot exported -> {path}")


@app.command("serve")
def serve(
    host: str = typer.Option(None, help="Bind host."),
    port: int = typer.Option(None, help="Bind port."),
    no_open: bool = typer.Option(False, "--no-open", help="Do not open browser automatically."),
) -> None:
    try:
        from cortex.webgraph.server import run_server
    except ImportError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    try:
        run_server(Path.cwd(), host=host, port=port, open_browser=not no_open)
    except ImportError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
